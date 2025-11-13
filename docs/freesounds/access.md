# Freesound.org API: Complete Guide for Programmatic Sample Downloads

> **⚠️ PROJECT IMPLEMENTATION NOTE**: The Amor project's `audio/download_freesound_library.py` script uses **OAuth2 authentication only** and downloads **original files only**. This document describes the full Freesound API capabilities for reference, but token authentication and preview downloads are not implemented in the codebase.

**Yes, you can absolutely build a script to automatically fetch audio samples from Freesound.org**, either by Freesound ID or by searching with specific criteria like tags, technical specs, and licenses. The API provides two download methods: **preview files** (compressed MP3/OGG, no OAuth2 required) for quick access, and **original files** (full-quality WAV/FLAC, OAuth2 required) for production use. Rate limits are generous at 60 requests/minute and 2,000/day for searches, with 500 original downloads allowed daily. The official Python library `freesound-python` handles authentication, pagination, and downloads seamlessly, making batch operations straightforward. 

## Getting API access takes minutes, not days

Registration is instant and free for non-commercial use. Visit https://freesound.org/apiv2/apply (login required) to generate API credentials immediately—no approval process or waiting period.  You’ll receive a **client ID** and **client secret/API key** displayed in a table on the same page.   Request separate keys for different applications as best practice.

Two authentication methods serve different purposes. **Token authentication** uses your API key for read-only operations: searching sounds and retrieving metadata. **OAuth2 authentication** is required for downloading original full-quality files, uploading sounds, or modifying content (rating, commenting, bookmarking). **The Amor project uses OAuth2 only** to ensure high-quality original downloads.

The standard RFC6749 authorization code flow involves three steps: redirecting users to authorize access, receiving a temporary authorization code (expires in 10 minutes), and exchanging it for an access token valid for 24 hours. Refresh tokens avoid repeated authorization flows. All OAuth2 requests must use HTTPS, and only one access token per application/user pair can exist at a time.  

## Search capabilities cover every technical specification you need

The Text Search endpoint (`GET /apiv2/search/text/`) serves as your primary discovery tool, supporting both keyword queries and sophisticated filtering.  The `query` parameter searches across tags, names, descriptions, pack names, and sound IDs—even empty queries return all sounds. The real power lies in the `filter` parameter using Solr syntax.  

**Technical specification filters** let you find precisely the samples you need. Filter by `samplerate:44100` for specific sample rates, `bitdepth:24` for 24-bit audio, `type:wav` or `type:flac` for lossless formats, `channels:2` for stereo, and `duration:[2 TO 10]` for length ranges.  Combine multiple conditions: `filter=samplerate:44100 type:wav channels:2 bitdepth:24` finds high-quality stereo WAV files at 44.1kHz.

**License filtering** is critical for your use case. Use `filter=license:"Creative Commons 0"` for CC0 (public domain, no attribution needed), `license:"Attribution"` for CC-BY (attribution required, commercial use OK), or `license:"Attribution Noncommercial"` for CC-BY-NC (non-commercial only).   Example: `filter=license:"Creative Commons 0" duration:[1 TO 5] tag:"singing bowl"` finds CC0 singing bowl samples between 1-5 seconds.

**AudioCommons descriptors** provide advanced audio feature filtering. Search by `ac_note_name:"A4"` for specific pitches, `ac_tempo:[118 TO 122]` for BPM ranges, `ac_loop:true` for loopable sounds, `ac_single_event:true` for single hits, and perceptual qualities like `ac_brightness`, `ac_warmth`, `ac_depth`, and `ac_hardness` (all 0-100 scales).  These descriptors enable content-based discovery beyond metadata.

The `fields` parameter optimizes API efficiency by specifying exactly which properties to return: `fields=id,name,previews,duration,samplerate,bitdepth,license,username,tags` gets everything needed for download decisions in one request.   Pagination handles large result sets with `page_size` up to 150 results per page (default: 15). Sort options include relevance score (default), upload date, duration, download count, and average rating. 

## Download Workflow for Original Files

**Original file downloads** (used by Amor project) require OAuth2 but deliver production-ready quality. After authenticating, use the endpoint `GET /apiv2/sounds/<sound_id>/download/` with the header `Authorization: Bearer ACCESS_TOKEN`. This returns the original uploaded file in its native format (WAV, AIFF, FLAC, OGG, or MP3) with full bit depth and sample rate preserved. The metadata endpoint reveals format details beforehand via the `type`, `samplerate`, `bitdepth`, and `channels` fields, letting you verify specifications before downloading.

**Downloading by Freesound ID**: Authenticate via OAuth2, call `client.get_sound(sound_id)` to retrieve metadata, then use `sound.retrieve("/path/to/save")` to download the original file.

**Note**: Preview downloads (`sound.retrieve_preview()`) are available via the API but not used in this project's implementation. 

## The official Python library handles complexity elegantly

The **freesound-python** library from Music Technology Group (the Freesound creators) provides the canonical Python implementation.  Install via `pip install git+https://github.com/MTG/freesound-python` or use the PyPI fork `pip install freesound-api`.   The library automatically maps function arguments to HTTP parameters, converts JSON responses to Python objects with dictionary fallback, and manages authentication sessions. 

OAuth2 setup (required for Amor project) uses `requests_oauthlib` for the authorization flow, then sets the access token:  

```python
from requests_oauthlib import OAuth2Session

oauth = OAuth2Session(client_id)
authorization_url, state = oauth.authorization_url(
    "https://freesound.org/apiv2/oauth2/authorize/"
)
# User visits authorization_url and grants access
authorization_code = input("Enter authorization code: ")
token = oauth.fetch_token(
    "https://freesound.org/apiv2/oauth2/access_token/",
    authorization_code=authorization_code,
    client_secret=client_secret
)

client = freesound.FreesoundClient()
client.set_token(token['access_token'], "oauth")
```

 

**Searching with filters** maps naturally to function parameters:

```python
results = client.text_search(
    query="singing bowl",
    filter='tag:"single note" license:"Creative Commons 0" bitdepth:24',
    fields="id,name,previews,duration,samplerate,bitdepth,license",
    page_size=50
)

for sound in results:
    print(f"{sound.id}: {sound.name} ({sound.duration}s, {sound.samplerate}Hz)")
```

**Batch downloading by ID list** (OAuth2 required for originals):

```python
sound_ids = [96541, 18763, 11532, 8734]

for sound_id in sound_ids:
    sound = client.get_sound(sound_id)
    sound.retrieve("./downloads", f"{sound.id}_{sound.name}.wav")
    print(f"Downloaded: {sound.name}")
```

**Batch downloading from search criteria** leverages pagination automatically:

```python
results = client.text_search(
    query="acoustic guitar",
    filter='tag:"single-note" duration:[1 TO 10] license:"Creative Commons 0"',
    fields="id,name,duration,samplerate,bitdepth,license",
    page_size=50
)

for sound in results:
    sound.retrieve("./downloads", f"{sound.id}_{sound.name}.wav")
```

The library handles pagination transparently—iterating over `results` automatically fetches subsequent pages. Access specific pages explicitly via `results.next_page()` and `results.previous_page()`.

## Rate limits are generous but require respect

**Standard limits** allow 60 requests per minute and 2,000 requests per day for general API operations (searches, metadata retrieval). **Restricted operations** (downloading originals, uploading, commenting, rating) have tighter limits: 30 requests per minute and 500 per day.   Critically, **original file downloads max at 500 sounds per day** regardless of request count. 

Exceeding limits returns HTTP 429 (“Too Many Requests”) with a detail field indicating which threshold was hit.   Limits apply per API key, not per user or IP.  The terms explicitly prohibit registering multiple keys to circumvent limitations—contact mtg@upf.edu if standard limits prove insufficient for legitimate use cases. 

**Best practices for bulk operations** center on efficiency and respect. Use the `fields` parameter to retrieve all needed metadata in search results, avoiding extra API calls for individual sounds. Request `page_size=150` (the maximum) for batch operations to minimize request count.

Implement rate limiting in code with sleep-based throttling (as used in `download_freesound_library.py`):

```python
import time

RATE_LIMIT_REQUESTS_PER_MINUTE = 29
for sound in results:
    sound.retrieve("./downloads", f"{sound.id}.wav")
    time.sleep(60.0 / RATE_LIMIT_REQUESTS_PER_MINUTE)
```

Setting 29 requests/minute provides safety margin below the 30/minute limit for downloads. Add exponential backoff when receiving 429 errors to avoid repeated limit violations.

## Licensing determines what you can build legally

Freesound supports four Creative Commons license types with distinct requirements. **CC0** (Creative Commons Zero) dedicates works to the public domain—no attribution required, commercial use permitted, maximum freedom. **CC-BY** (Attribution) requires crediting the sound creator with name, sound title, Freesound URL, and license type, but allows commercial use and modifications. **CC-BY-NC** (Attribution-NonCommercial) mandates attribution and prohibits commercial use entirely.  **Sampling Plus** is a deprecated legacy license similar to CC-BY-NC, being phased out as users update preferences. 

**Attribution format** for CC-BY and CC-BY-NC must include:

```
"sound_name" by username (http://freesound.org/s/sound_id/) licensed under CC-BY 4.0
```

Freesound provides an attribution list at https://freesound.org/home/attribution/ showing all sounds downloaded by your account.  For CC0 sounds, attribution is appreciated but legally optional—however, you cannot claim authorship of the original sound.

**Commercial API use** requires separate licensing beyond sound-level licenses. The API itself is free only for non-commercial purposes (research, education, personal projects). Commercial applications that generate revenue must negotiate a commercial API license by contacting mtg@upf.edu—companies like Spotify, Google, and Waves Audio have such agreements.  Importantly, a commercial API license doesn’t override individual sound licenses: CC-BY-NC sounds remain non-commercial regardless of API licensing status. 

**Database replication is explicitly prohibited**. Terms forbid downloading the entire Freesound database or creating mirror sites.  Bulk downloading for legitimate projects is fine, but respect server resources and only download what you genuinely need. For extensive data needs, contact the Freesound team to discuss appropriate arrangements.

## Complete workflow example (OAuth2 + original files)

Here's the approach used in `audio/download_freesound_library.py`:

```python
import freesound
from pathlib import Path
import time

# Setup with OAuth2 (see OAuth2 setup section above for token acquisition)
client = freesound.FreesoundClient()
client.set_token(access_token, "oauth")
output_dir = Path("./sounds")
output_dir.mkdir(exist_ok=True)

# Search for samples matching criteria
results = client.text_search(
    query="singing bowl",
    filter='tag:"single note" license:"Creative Commons 0" bitdepth:24 duration:[1 TO 10]',
    fields="id,name,duration,samplerate,bitdepth,license,username,tags",
    page_size=150,
    sort="rating_desc"
)

# Track downloads and metadata
metadata_list = []
downloaded = 0
RATE_LIMIT = 29  # requests per minute

print(f"Found {results.count} matching sounds. Downloading...\n")

for sound in results:
    try:
        # Download original file
        filename = f"{sound.id}_{sound.name}"
        sound.retrieve(str(output_dir), filename)

        # Save metadata
        metadata_list.append({
            'id': sound.id,
            'name': sound.name,
            'username': sound.username,
            'license': sound.license,
            'url': f"https://freesound.org/s/{sound.id}/",
            'duration': sound.duration,
            'samplerate': sound.samplerate,
            'bitdepth': sound.bitdepth,
            'tags': sound.tags if hasattr(sound, 'tags') else []
        })

        downloaded += 1
        print(f"✓ {downloaded}: {sound.name} ({sound.duration}s)")

        # Rate limiting
        time.sleep(60.0 / RATE_LIMIT)

    except Exception as e:
        print(f"✗ Error downloading {sound.name}: {e}")

# Save metadata
import json
with open(output_dir / "metadata.json", "w") as f:
    json.dump(metadata_list, f, indent=2)

print(f"\n✅ Downloaded {downloaded} sounds to {output_dir}")
```

## Key limitations and considerations

**Format consistency**: Preview downloads always produce MP3 or OGG files regardless of original format. Original downloads preserve native formats (WAV, AIFF, FLAC, OGG, MP3), requiring format detection and handling multiple file types in your pipeline.  

**Quality tradeoff**: Previews use lossy compression (64-192kbps) suitable for testing but potentially problematic for production sound design.  Original downloads require OAuth2 authentication, adding implementation complexity but delivering full fidelity.  

**Daily download caps**: The 500 original downloads per day limit means downloading large sample libraries requires multiple days or requesting increased limits.  Preview downloads have no explicit daily limit beyond the 2,000 general API requests cap.

**License verification**: Always check the `license` field before downloading. Sounds uploaded before license system updates may have different licensing than expected. Filter by license in searches to ensure compliance with your intended use.

**Authentication tokens expire**: OAuth2 access tokens last 24 hours.   Implement refresh token logic for long-running batch operations spanning multiple days.  Token authentication never expires but requires keeping API keys secure.

**Network efficiency**: Download operations consume bandwidth—implement retry logic with exponential backoff for network failures. Stream large files rather than loading entirely into memory. The `requests` library’s `stream=True` parameter handles this automatically.

## Your specific question: Can you build the script?

**Absolutely yes**. Both approaches you described are fully supported:

1. **Downloading by Freesound ID**: Given a list of IDs, use `client.get_sound(sound_id)` followed by `sound.retrieve_preview()` or `sound.retrieve()` (for originals with OAuth2). This method works perfectly for fetching samples identified in your research guide.  
1. **Searching by criteria**: Use `client.text_search()` with filter strings combining tags (`tag:"singing bowl single note"`), license (`license:"Creative Commons 0"`), and technical specs (`bitdepth:24 samplerate:44100`). Iterate results and download matches.

**For your use case** (downloading samples matching specific criteria like "singing bowl single note" with CC0 license and 24-bit depth), the search-based approach lets you discover and download in one workflow without manual ID collection. The filter syntax supports all parameters you mentioned: tags, license type, bit depth, sample rate, duration, and more.

**The Amor project uses OAuth2 and original downloads** to ensure production-quality audio files with full fidelity.  

The API provides everything needed for automated batch downloading—the only constraints are rate limits (generous for most use cases) and licensing requirements (resolvable by filtering for CC0 or implementing proper attribution). The official Python library handles the technical complexity, leaving you to focus on search criteria and file management logic.

## Conclusion: A mature API ready for production use

Freesound’s API has reached maturity with comprehensive documentation, official library support, and generous rate limits for legitimate batch operations.   The ability to filter by technical specifications (sample rate, bit depth, duration), license type, and audio features (pitch, tempo, timbre) makes programmatic discovery of specific samples straightforward.  Download workflows accommodate both quick preview access and full-quality original retrieval, trading authentication complexity for audio fidelity. 

Building your automated download script is entirely feasible—choose preview downloads for simplicity and speed, or implement OAuth2 for production-quality originals. The official `freesound-python` library eliminates low-level HTTP handling, and rate limits of 60 requests/minute with 2,000/day allow downloading hundreds of samples daily within terms of service.  Filter by `license:"Creative Commons 0"` to avoid attribution requirements, or implement proper credit generation for CC-BY sounds.

Start with token authentication and preview downloads for immediate results, then add OAuth2 support if full-quality originals become necessary. The API’s design and the Python library’s abstractions make both paths straightforward to implement.