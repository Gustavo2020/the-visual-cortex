import argparse
import hashlib
import os
import signal
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


def build_session(user_agent: str, timeout: int, retries: int = 5, backoff: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "image/*, */*;q=0.8",
    })
    # Store default timeout on session for convenience
    session.request = _with_default_timeout(session.request, timeout)
    return session


def _with_default_timeout(request_func, timeout_default: int):
    def wrapper(*args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout_default
        # request_func is already bound to the session, so we preserve the original
        # arguments (including self) and only inject the timeout when missing.
        return request_func(*args, **kwargs)

    return wrapper


def ext_from_content_type(ct: Optional[str]) -> Optional[str]:
    if not ct:
        return None
    ct = ct.split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
    }
    return mapping.get(ct)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_existing_hashes(path: Path) -> Set[str]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    hashes: Set[str] = set()
    for p in path.iterdir():
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        try:
            hashes.add(sha256_bytes(p.read_bytes()))
        except Exception:
            continue
    return hashes


def is_reasonable_image(response: requests.Response, min_bytes: int) -> bool:
    if response.status_code != 200:
        return False
    if not response.content or len(response.content) < min_bytes:
        return False
    ct = response.headers.get("Content-Type", "").lower()
    if not ct.startswith("image/"):
        return False
    return True


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def count_existing_images(path: Path) -> int:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    return sum(1 for p in path.iterdir() if p.is_file() and p.suffix.lower() in exts)


def download_one(
    session: requests.Session,
    url: str,
    dest_dir: Path,
    min_bytes: int,
    sleep_ok: float,
    existing_hashes: Set[str],
    filename_prefix: str = "IMG_",
) -> Optional[Path]:
    try:
        resp = session.get(url, allow_redirects=True)
    except Exception:
        return None

    if not is_reasonable_image(resp, min_bytes):
        return None

    ct = resp.headers.get("Content-Type")
    ext = ext_from_content_type(ct) or ".jpg"

    # Ensure we never overwrite existing files; regenerate name if collision.
    for _ in range(5):
        candidate = dest_dir / f"{filename_prefix}{uuid.uuid4().hex[:8]}{ext}"
        if not candidate.exists():
            path = candidate
            break
    else:
        path = dest_dir / f"{filename_prefix}{uuid.uuid4().hex}{ext}"

    try:
        data = resp.content
        file_hash = sha256_bytes(data)
        if file_hash in existing_hashes:
            return None
        path.write_bytes(data)
        existing_hashes.add(file_hash)
        if sleep_ok > 0:
            time.sleep(sleep_ok)
        return path
    except Exception:
        return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Download random images from Unsplash Source with retries and validation.")
    parser.add_argument("--num-images", type=int, default=100, help="Number of new images to download (not total).")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to store images. Default: data/images in repository root.")
    parser.add_argument("--width", type=int, default=800, help="Image width.")
    parser.add_argument("--height", type=int, default=600, help="Image height.")
    parser.add_argument("--min-bytes", type=int, default=10_000, help="Minimum response size to accept as image.")
    parser.add_argument("--timeout", type=int, default=15, help="Per-request timeout in seconds.")
    parser.add_argument("--max-attempts", type=int, default=None, help="Max attempts to reach the target number of images. Default: num_images * 3.")
    parser.add_argument("--sleep-ok", type=float, default=0.5, help="Sleep seconds after a successful download to avoid rate limits.")
    parser.add_argument("--sleep-fail", type=float, default=1.0, help="Sleep seconds after a failed attempt.")
    parser.add_argument("--user-agent", type=str, default="the-visual-cortex-downloader/1.0", help="HTTP User-Agent to use.")
    parser.add_argument("--retries", type=int, default=5, help="HTTP retries for transient errors.")
    parser.add_argument("--backoff", type=float, default=0.5, help="Exponential backoff factor for retries.")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent download workers (use cautiously; default 1).")
    parser.add_argument("--max-seconds", type=int, default=0, help="Stop after this many seconds (0 = no limit).")
    parser.add_argument("--provider", choices=["unsplash", "picsum", "custom"], default="unsplash", help="Image provider to use.")
    parser.add_argument("--url", type=str, default=None, help="Custom image URL (used when --provider=custom). Can include {width} and {height} placeholders.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent  # Go up to repository root
    output_dir = args.output_dir or (repo_root / "data" / "images")
    ensure_dir(output_dir)

    existing_hashes = load_existing_hashes(output_dir)

    if args.provider == "unsplash":
        url = f"https://source.unsplash.com/{args.width}x{args.height}"
    elif args.provider == "picsum":
        url = f"https://picsum.photos/{args.width}/{args.height}?random"
        # picsum respects caching, random adds variance
    elif args.provider == "custom":
        if not args.url:
            print("--url is required when --provider=custom", file=sys.stderr)
            return 2
        url = args.url.format(width=args.width, height=args.height)
    else:
        print(f"Unknown provider: {args.provider}", file=sys.stderr)
        return 2

    existing = count_existing_images(output_dir)
    remaining = max(args.num_images, 0)

    if remaining == 0:
        print(f"Already have {existing} images in {output_dir}. Nothing to download.")
        return 0

    max_attempts = args.max_attempts if args.max_attempts is not None else remaining * 3

    session = build_session(user_agent=args.user_agent, timeout=args.timeout, retries=args.retries, backoff=args.backoff)

    stop_at = time.time() + args.max_seconds if args.max_seconds and args.max_seconds > 0 else None

    downloaded = 0
    attempts = 0

    def time_exceeded() -> bool:
        return stop_at is not None and time.time() >= stop_at

    interrupted = False

    def handle_sigint(signum, frame):
        nonlocal interrupted
        interrupted = True

    prev_handler = signal.signal(signal.SIGINT, handle_sigint)

    try:
        if args.workers <= 1:
            with tqdm(total=remaining, desc="Downloading images") as pbar:
                while downloaded < remaining and attempts < max_attempts and not interrupted and not time_exceeded():
                    attempts += 1
                    path = download_one(session, url, output_dir, args.min_bytes, args.sleep_ok, existing_hashes)
                    if path is not None:
                        downloaded += 1
                        pbar.update(1)
                    else:
                        if args.sleep_fail > 0:
                            time.sleep(args.sleep_fail)
        else:
            # Cautious parallelism: submit one task per attempt until done
            with tqdm(total=remaining, desc="Downloading images") as pbar:
                with ThreadPoolExecutor(max_workers=args.workers) as ex:
                    futures = set()
                    while (downloaded < remaining) and (attempts < max_attempts) and not interrupted and not time_exceeded():
                        # Keep queue modest: no more than workers pending
                        while len(futures) < args.workers and attempts < max_attempts and not time_exceeded():
                            attempts += 1
                            futures.add(ex.submit(download_one, session, url, output_dir, args.min_bytes, args.sleep_ok, existing_hashes))

                        if not futures:
                            break

                        done, futures = wait_first(futures)
                        for fut in done:
                            path = fut.result()
                            if path is not None:
                                downloaded += 1
                                pbar.update(1)
                            else:
                                if args.sleep_fail > 0:
                                    time.sleep(args.sleep_fail)
                            if downloaded >= remaining or interrupted or time_exceeded():
                                break
    finally:
        signal.signal(signal.SIGINT, prev_handler)

    print(f"Downloaded {downloaded} images (attempts: {attempts}, existing: {existing}) to {output_dir}.")
    if interrupted:
        print("Interrupted by user (Ctrl+C).")
    if time_exceeded():
        print("Stopped due to max-seconds limit.")
    return 0


def wait_first(futures):
    done = set()
    try:
        for fut in as_completed(futures, timeout=1.0):
            done.add(fut)
            # Pull one or more completed futures quickly
            if len(done) > 0:
                break
    except Exception:
        # Timeout or other: return empty done to allow loop to continue
        pass
    return done, futures - done


if __name__ == "__main__":
    sys.exit(main())
