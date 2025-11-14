#!/usr/bin/env python3
"""
Freesound Sample Library Downloader

Downloads curated audio samples from Freesound.org for the Corazonn heartbeat
installation. Organizes samples by timbral family and captures comprehensive
metadata for programmatic exploration and bank curation.

Usage:
    # First time: authenticate with Freesound
    ./download_freesound_library.py auth

    # Download all samples
    ./download_freesound_library.py download

    # Download specific timbral family
    ./download_freesound_library.py download --family 01_Metallic_Bells

    # Update metadata for existing library
    ./download_freesound_library.py update-metadata

    # Verify downloads against freesound_ids.yaml
    ./download_freesound_library.py verify

Requirements:
    - Freesound.org account with API credentials
    - .env file with FREESOUND_CLIENT_ID and FREESOUND_CLIENT_SECRET
    - Internet connection

Author: Claude Code
License: See repository license
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlencode

import yaml

# Check for required dependencies
try:
    import freesound
except ImportError:
    print("ERROR: freesound-python not installed")
    print("Install with: pip install git+https://github.com/MTG/freesound-python")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed")
    print("Install with: pip install python-dotenv")
    sys.exit(1)

try:
    from requests_oauthlib import OAuth2Session
except ImportError:
    print("ERROR: requests-oauthlib not installed")
    print("Install with: pip install requests-oauthlib")
    sys.exit(1)


# Constants
PROJECT_ROOT = Path(__file__).parent.parent
LIBRARY_ROOT = PROJECT_ROOT / "audio" / "library"
IDS_FILE = PROJECT_ROOT / "audio" / "freesound_ids.yaml"
ENV_FILE = PROJECT_ROOT / ".env"
METADATA_FILE = LIBRARY_ROOT / "metadata.json"
ATTRIBUTION_FILE = LIBRARY_ROOT / "attribution.txt"

FREESOUND_AUTH_URL = "https://freesound.org/apiv2/oauth2/authorize/"
FREESOUND_TOKEN_URL = "https://freesound.org/apiv2/oauth2/access_token/"

# Rate limiting: Downloads are restricted operations at 30/min, not 60/min
# Each sample requires 2 calls (metadata fetch + download), so limit to 29/min
RATE_LIMIT_REQUESTS_PER_MINUTE = 29  # Leave margin under 30/min download limit
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = [2, 4, 8, 16]  # Exponential backoff in seconds


class FreesoundDownloader:
    """Manages downloading and organizing Freesound samples."""

    def __init__(self):
        """Initialize downloader with configuration."""
        load_dotenv(ENV_FILE)

        self.client_id = os.getenv("FREESOUND_CLIENT_ID")
        self.client_secret = os.getenv("FREESOUND_CLIENT_SECRET")
        self.access_token = os.getenv("FREESOUND_ACCESS_TOKEN")
        self.refresh_token = os.getenv("FREESOUND_REFRESH_TOKEN")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"Missing Freesound credentials in {ENV_FILE}\n"
                "Get credentials from: https://freesound.org/apiv2/apply"
            )

        self.client = None
        self.sample_ids = None
        self.metadata_db = {"samples": [], "library_version": "1.0"}

    def authenticate(self):
        """Perform OAuth2 authentication flow and store tokens."""
        print("=" * 70)
        print("FREESOUND OAUTH2 AUTHENTICATION")
        print("=" * 70)
        print()

        oauth = OAuth2Session(
            self.client_id,
            redirect_uri="https://localhost/callback"
        )

        authorization_url, state = oauth.authorization_url(FREESOUND_AUTH_URL)

        print("1. Visit this URL in your browser:")
        print()
        print(f"   {authorization_url}")
        print()
        print("2. Authorize the application")
        print("3. You'll be redirected to localhost (which will fail - that's OK!)")
        print("4. Copy the ENTIRE URL from your browser's address bar")
        print()

        callback_url = input("Paste the full callback URL here: ").strip()

        try:
            # Extract the authorization response
            token = oauth.fetch_token(
                FREESOUND_TOKEN_URL,
                authorization_response=callback_url,
                client_secret=self.client_secret
            )

            # Update .env file with tokens
            self._update_env_tokens(
                token.get("access_token"),
                token.get("refresh_token")
            )

            print()
            print("✓ Authentication successful!")
            print(f"✓ Tokens saved to {ENV_FILE}")
            print()
            print("You can now run: ./download_freesound_library.py download")

        except Exception as e:
            print(f"\n✗ Authentication failed: {e}")
            sys.exit(1)

    def _update_env_tokens(self, access_token: str, refresh_token: str):
        """Update .env file with new OAuth2 tokens."""
        env_content = []

        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                env_content = f.readlines()

        # Update or add token lines
        access_line = f"FREESOUND_ACCESS_TOKEN={access_token}\n"
        refresh_line = f"FREESOUND_REFRESH_TOKEN={refresh_token}\n"

        access_found = False
        refresh_found = False

        for i, line in enumerate(env_content):
            if line.startswith("FREESOUND_ACCESS_TOKEN="):
                env_content[i] = access_line
                access_found = True
            elif line.startswith("FREESOUND_REFRESH_TOKEN="):
                env_content[i] = refresh_line
                refresh_found = True

        if not access_found:
            env_content.append(access_line)
        if not refresh_found:
            env_content.append(refresh_line)

        with open(ENV_FILE, 'w') as f:
            f.writelines(env_content)

        # Reload environment
        load_dotenv(ENV_FILE, override=True)
        self.access_token = access_token
        self.refresh_token = refresh_token

    def _refresh_access_token(self) -> bool:
        """
        Refresh expired OAuth2 access token using refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            return False

        try:
            oauth = OAuth2Session(
                self.client_id,
                token={'refresh_token': self.refresh_token}
            )

            new_token = oauth.refresh_token(
                FREESOUND_TOKEN_URL,
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            # Update tokens
            self._update_env_tokens(
                new_token.get('access_token'),
                new_token.get('refresh_token')
            )

            # Reinitialize client with new token
            self._init_client()

            print("✓ OAuth2 token refreshed")
            return True

        except Exception as e:
            print(f"✗ Token refresh failed: {e}")
            return False

    def _init_client(self):
        """Initialize Freesound client with OAuth2 token."""
        if not self.access_token:
            raise ValueError(
                "No access token found. Run authentication first:\n"
                "  ./download_freesound_library.py auth"
            )

        self.client = freesound.FreesoundClient()
        self.client.set_token(self.access_token, "oauth")

    def load_sample_ids(self) -> Dict[str, List[Dict]]:
        """Load sample IDs from YAML configuration."""
        if not IDS_FILE.exists():
            raise FileNotFoundError(f"Sample IDs file not found: {IDS_FILE}")

        with open(IDS_FILE, 'r') as f:
            self.sample_ids = yaml.safe_load(f)

        return self.sample_ids

    def download_library(self, family_filter: Optional[str] = None, limit: Optional[int] = None):
        """
        Download sample library organized by timbral families.

        Args:
            family_filter: Only download specific family (e.g., "01_Metallic_Bells")
            limit: Maximum number of samples to download (for testing)
        """
        self._init_client()
        self.load_sample_ids()

        # Load existing metadata to avoid overwriting in multi-session downloads
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                self.metadata_db = json.load(f)
                # Ensure 'samples' key exists
                if 'samples' not in self.metadata_db:
                    self.metadata_db['samples'] = []

        # Ensure library root exists
        LIBRARY_ROOT.mkdir(exist_ok=True)

        # Filter families if requested
        families_to_process = {}
        if family_filter:
            if family_filter in self.sample_ids:
                families_to_process = {family_filter: self.sample_ids[family_filter]}
            else:
                print(f"✗ Family not found: {family_filter}")
                print(f"Available families: {', '.join(self.sample_ids.keys())}")
                return
        else:
            families_to_process = self.sample_ids

        # Count total samples
        total_samples = sum(
            len(samples) if samples else 0
            for family_data in families_to_process.values()
            for samples in family_data.values()
        )

        if limit:
            total_samples = min(total_samples, limit)

        print("=" * 70)
        print("FREESOUND LIBRARY DOWNLOAD")
        print("=" * 70)
        print(f"Families: {len(families_to_process)}")
        print(f"Total samples: {total_samples}")
        print(f"Library: {LIBRARY_ROOT}")
        print("=" * 70)
        print()

        downloaded = 0
        skipped = 0
        failed = 0

        for family_name, family_data in families_to_process.items():
            print(f"\n{'=' * 70}")
            print(f"FAMILY: {family_name}")
            print(f"{'=' * 70}\n")

            # Create family directory (flat structure)
            family_dir = LIBRARY_ROOT / family_name
            family_dir.mkdir(exist_ok=True)

            for subfamily_name, samples in family_data.items():
                if not samples:
                    continue

                print(f"\n  Subfamily: {subfamily_name}")
                print(f"  {'-' * 60}")

                for sample_info in samples:
                    if limit and downloaded >= limit:
                        print(f"\n  Reached download limit: {limit}")
                        break

                    sound_id = sample_info['id']

                    try:
                        # Build filename
                        instrument = sample_info['instrument']
                        pitch = sample_info.get('pitch', 'X')
                        if pitch is None:
                            pitch = 'X'

                        # Fetch sound metadata
                        print(f"  [{downloaded + 1}/{total_samples}] ID {sound_id}: ", end="", flush=True)

                        sound = self._fetch_with_retry(sound_id)

                        if sound is None:
                            print(f"✗ FAILED to fetch metadata")
                            failed += 1
                            continue

                        # Determine file extension from original format
                        file_ext = self._get_file_extension(sound)
                        filename = f"{instrument}_{pitch}_{sound_id}.{file_ext}"
                        filepath = family_dir / filename

                        # Check if already downloaded
                        if filepath.exists():
                            print(f"✓ EXISTS ({sound.name})")
                            skipped += 1

                            # Still collect metadata if not in database
                            if not any(s['freesound_id'] == sound_id for s in self.metadata_db['samples']):
                                self._collect_metadata(sound, sample_info, family_name, subfamily_name, filepath)

                            continue

                        # Download original file
                        download_success = self._download_with_retry(sound, filepath)

                        if download_success:
                            print(f"✓ DOWNLOADED ({sound.name})")
                            downloaded += 1

                            # Collect metadata
                            self._collect_metadata(sound, sample_info, family_name, subfamily_name, filepath)
                        else:
                            print(f"✗ FAILED download")
                            failed += 1

                        # Rate limiting
                        time.sleep(60.0 / RATE_LIMIT_REQUESTS_PER_MINUTE)

                    except KeyboardInterrupt:
                        print("\n\n✗ Download interrupted by user")
                        break
                    except Exception as e:
                        print(f"✗ ERROR: {e}")
                        failed += 1

        # Save metadata and attribution
        self._save_metadata()
        self._generate_attribution()

        # Summary
        print("\n" + "=" * 70)
        print("DOWNLOAD COMPLETE")
        print("=" * 70)
        print(f"✓ Downloaded: {downloaded}")
        print(f"⊘ Skipped (existing): {skipped}")
        print(f"✗ Failed: {failed}")
        print(f"📄 Metadata: {METADATA_FILE}")
        print(f"📝 Attribution: {ATTRIBUTION_FILE}")
        print("=" * 70)

    def _fetch_with_retry(self, sound_id: int):
        """Fetch sound metadata with retry logic."""
        token_refreshed = False

        for attempt in range(RETRY_ATTEMPTS):
            try:
                sound = self.client.get_sound(
                    sound_id,
                    fields="id,name,username,license,duration,samplerate,bitdepth,"
                           "channels,filesize,type,tags,description,created,download,"
                           "previews,num_downloads,avg_rating,num_ratings,ac_analysis"
                )
                return sound
            except Exception as e:
                error_msg = str(e).lower()

                # Handle specific error types
                if '404' in error_msg or 'not found' in error_msg:
                    # Don't retry for missing sounds
                    return None
                elif ('401' in error_msg or 'unauthorized' in error_msg) and not token_refreshed:
                    # Try refreshing token once
                    if self._refresh_access_token():
                        token_refreshed = True
                        continue  # Retry with new token
                    else:
                        raise ValueError("Authentication failed - run 'auth' command")

                # Retry with exponential backoff for other errors
                if attempt < RETRY_ATTEMPTS - 1:
                    wait_time = RETRY_BACKOFF[attempt]
                    time.sleep(wait_time)
                else:
                    return None
        return None

    def _download_with_retry(self, sound, filepath: Path) -> bool:
        """Download sound file with retry logic."""
        token_refreshed = False

        for attempt in range(RETRY_ATTEMPTS):
            try:
                sound.retrieve(str(filepath.parent), filepath.name)
                return True
            except Exception as e:
                error_msg = str(e).lower()

                # Handle auth errors
                if ('401' in error_msg or 'unauthorized' in error_msg) and not token_refreshed:
                    # Try refreshing token once
                    if self._refresh_access_token():
                        token_refreshed = True
                        continue  # Retry with new token
                    else:
                        return False

                # Retry with exponential backoff for other errors
                if attempt < RETRY_ATTEMPTS - 1:
                    wait_time = RETRY_BACKOFF[attempt]
                    time.sleep(wait_time)
                else:
                    print(f"(Error: {str(e)[:60]})")
                    return False
        return False

    def _get_file_extension(self, sound) -> str:
        """Determine file extension from sound type."""
        sound_type = getattr(sound, 'type', 'wav').lower()

        # Map Freesound types to extensions
        type_map = {
            'wav': 'wav',
            'aiff': 'aif',
            'aif': 'aif',
            'flac': 'flac',
            'ogg': 'ogg',
            'mp3': 'mp3'
        }

        return type_map.get(sound_type, 'wav')

    def _collect_metadata(self, sound, sample_info: Dict, family: str, subfamily: str, filepath: Path):
        """Collect comprehensive metadata for a downloaded sample."""

        # Extract audio features if available
        audio_features = {}
        if hasattr(sound, 'ac_analysis'):
            ac = sound.ac_analysis
            if ac:
                audio_features = {
                    'loudness': getattr(ac, 'loudness', None),
                    'dynamic_range': getattr(ac, 'dynamic_range', None),
                    'temporal_centroid': getattr(ac, 'temporal_centroid', None),
                    'log_attack_time': getattr(ac, 'log_attack_time', None),
                }

        metadata = {
            'file_path': str(filepath.relative_to(PROJECT_ROOT)),
            'freesound_id': sound.id,
            'freesound_url': f"https://freesound.org/s/{sound.id}/",
            'username': getattr(sound, 'username', 'unknown'),
            'name': getattr(sound, 'name', 'unknown'),
            'license': getattr(sound, 'license', 'unknown'),
            'timbral_family': family,
            'subfamily': subfamily,
            'instrument': sample_info.get('instrument', 'unknown'),
            'pitch': sample_info.get('pitch'),
            'description_plan': sample_info.get('description', ''),
            'description_freesound': getattr(sound, 'description', ''),
            'duration_sec': getattr(sound, 'duration', None),
            'samplerate': getattr(sound, 'samplerate', None),
            'bitdepth': getattr(sound, 'bitdepth', None),
            'channels': getattr(sound, 'channels', None),
            'filesize_bytes': getattr(sound, 'filesize', None),
            'file_type': getattr(sound, 'type', None),
            'tags': getattr(sound, 'tags', []),
            'created': getattr(sound, 'created', None),
            'num_downloads': getattr(sound, 'num_downloads', None),
            'avg_rating': getattr(sound, 'avg_rating', None),
            'num_ratings': getattr(sound, 'num_ratings', None),
            'audio_features': audio_features,
            'download_date': datetime.now().isoformat(),
        }

        self.metadata_db['samples'].append(metadata)

    def _save_metadata(self):
        """Save metadata database to JSON file."""
        self.metadata_db['library_version'] = "1.0"
        self.metadata_db['total_samples'] = len(self.metadata_db['samples'])
        self.metadata_db['generated_date'] = datetime.now().isoformat()

        with open(METADATA_FILE, 'w') as f:
            json.dump(self.metadata_db, f, indent=2)

    def _generate_attribution(self):
        """Generate attribution file for license compliance."""
        with open(ATTRIBUTION_FILE, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("FREESOUND.ORG SAMPLE ATTRIBUTION\n")
            f.write("Corazonn Heartbeat Installation Sample Library\n")
            f.write("=" * 70 + "\n\n")

            # Group by license
            by_license = {}
            for sample in self.metadata_db['samples']:
                license_type = sample['license']
                if license_type not in by_license:
                    by_license[license_type] = []
                by_license[license_type].append(sample)

            # Write attribution by license type
            for license_type, samples in sorted(by_license.items()):
                f.write(f"\n{license_type}\n")
                f.write("-" * 70 + "\n\n")

                for sample in sorted(samples, key=lambda s: s['freesound_id']):
                    f.write(f'"{sample["name"]}" by {sample["username"]}\n')
                    f.write(f'  {sample["freesound_url"]}\n')
                    f.write(f'  License: {sample["license"]}\n\n')

            f.write("\n" + "=" * 70 + "\n")
            f.write(f"Total samples: {len(self.metadata_db['samples'])}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n")

    def update_metadata(self):
        """Update metadata for existing library files."""
        print("Updating metadata for existing library...")

        self._init_client()
        self.load_sample_ids()

        # Load existing metadata if available
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                self.metadata_db = json.load(f)

        # Scan library directory
        for family_name, family_data in self.sample_ids.items():
            family_dir = LIBRARY_ROOT / family_name

            if not family_dir.exists():
                continue

            for subfamily_name, samples in family_data.items():
                if not samples:
                    continue

                for sample_info in samples:
                    sound_id = sample_info['id']

                    # Check if metadata already exists
                    if any(s['freesound_id'] == sound_id for s in self.metadata_db['samples']):
                        continue

                    # Find file for this ID
                    matching_files = list(family_dir.glob(f"*_{sound_id}.*"))
                    if not matching_files:
                        continue

                    filepath = matching_files[0]

                    try:
                        print(f"Fetching metadata for ID {sound_id}...")
                        sound = self._fetch_with_retry(sound_id)

                        if sound:
                            self._collect_metadata(sound, sample_info, family_name, subfamily_name, filepath)

                        time.sleep(60.0 / RATE_LIMIT_REQUESTS_PER_MINUTE)

                    except Exception as e:
                        print(f"✗ Error fetching metadata for {sound_id}: {e}")

        self._save_metadata()
        self._generate_attribution()

        print(f"✓ Metadata updated: {METADATA_FILE}")

    def verify(self):
        """Verify downloaded files against sample IDs configuration."""
        self.load_sample_ids()

        print("=" * 70)
        print("LIBRARY VERIFICATION")
        print("=" * 70)

        missing = []
        present = []

        for family_name, family_data in self.sample_ids.items():
            family_dir = LIBRARY_ROOT / family_name

            print(f"\n{family_name}:")

            for subfamily_name, samples in family_data.items():
                if not samples:
                    continue

                for sample_info in samples:
                    sound_id = sample_info['id']
                    instrument = sample_info['instrument']

                    # Look for any file with this ID
                    matching_files = []
                    if family_dir.exists():
                        matching_files = list(family_dir.glob(f"*_{sound_id}.*"))

                    if matching_files:
                        print(f"  ✓ {sound_id} ({instrument})")
                        present.append(sound_id)
                    else:
                        print(f"  ✗ {sound_id} ({instrument}) - MISSING")
                        missing.append(sound_id)

        print("\n" + "=" * 70)
        print(f"✓ Present: {len(present)}")
        print(f"✗ Missing: {len(missing)}")
        print("=" * 70)

        if missing:
            print(f"\nMissing IDs: {', '.join(map(str, missing))}")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Download and organize Freesound samples for Corazonn heartbeat installation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First time setup
  %(prog)s auth

  # Download all samples
  %(prog)s download

  # Download specific family
  %(prog)s download --family 01_Metallic_Bells

  # Test download (limit to 5 samples)
  %(prog)s download --limit 5

  # Update metadata for existing files
  %(prog)s update-metadata

  # Verify downloads
  %(prog)s verify
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Auth command
    subparsers.add_parser('auth', help='Authenticate with Freesound OAuth2')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download sample library')
    download_parser.add_argument(
        '--family',
        help='Download only specific timbral family (e.g., 01_Metallic_Bells)'
    )
    download_parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of samples to download (for testing)'
    )

    # Update metadata command
    subparsers.add_parser('update-metadata', help='Update metadata for existing library')

    # Verify command
    subparsers.add_parser('verify', help='Verify downloaded files')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        downloader = FreesoundDownloader()

        if args.command == 'auth':
            downloader.authenticate()
        elif args.command == 'download':
            downloader.download_library(
                family_filter=args.family,
                limit=args.limit
            )
        elif args.command == 'update-metadata':
            downloader.update_metadata()
        elif args.command == 'verify':
            downloader.verify()

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
