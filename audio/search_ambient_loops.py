#!/usr/bin/env python3
"""
Search Freesound for ambient nature loops.

Tests different search queries to validate keyword effectiveness before batch downloading.
Returns results with ratings, downloads, duration, tags for evaluation.

Usage:
    # Search all categories
    ./audio/search_ambient_loops.py

    # Search specific category
    ./audio/search_ambient_loops.py --category ocean

    # Show detailed results
    ./audio/search_ambient_loops.py --verbose

    # Export results to JSON
    ./audio/search_ambient_loops.py --output results.json

Requirements:
    - Authenticated with Freesound (run download_freesound_library.py auth first)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

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


# Search queries organized by category
SEARCH_QUERIES = {
    'ocean': [
        {
            'query': 'ocean waves',
            'filter': 'license:"Creative Commons 0" duration:[60 TO 120] tag:seamless',
            'description': 'CC0 seamless ocean waves (60-120s)'
        },
        {
            'query': 'gentle surf',
            'filter': 'license:"Creative Commons 0" duration:[45 TO 90] tag:loop',
            'description': 'CC0 gentle surf loops (45-90s)'
        },
        {
            'query': 'beach waves',
            'filter': 'duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'Beach waves seamless/loop (60-120s, any license)'
        },
        {
            'query': 'underwater ambience',
            'filter': 'duration:[30 TO 90]',
            'description': 'Underwater ambience (30-90s)'
        },
    ],
    'rain': [
        {
            'query': 'light rain',
            'filter': 'license:"Creative Commons 0" duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'CC0 light rain loops (60-120s)'
        },
        {
            'query': 'rain on leaves',
            'filter': 'duration:[45 TO 90] tag:loop',
            'description': 'Rain on leaves loops (45-90s)'
        },
        {
            'query': 'heavy rain',
            'filter': 'duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'Heavy rain seamless (60-120s)'
        },
    ],
    'forest': [
        {
            'query': 'forest birds',
            'filter': 'license:"Creative Commons 0" duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'CC0 forest bird loops (60-120s)'
        },
        {
            'query': 'dawn chorus',
            'filter': 'duration:[60 TO 120] tag:loop',
            'description': 'Dawn chorus loops (60-120s)'
        },
        {
            'query': 'forest ambience',
            'filter': 'duration:[45 TO 90] (tag:seamless OR tag:loop)',
            'description': 'Forest ambience loops (45-90s)'
        },
        {
            'query': 'birds chirping',
            'filter': 'duration:[30 TO 90] tag:loop',
            'description': 'Bird chirping loops (30-90s)'
        },
    ],
    'wind': [
        {
            'query': 'wind leaves',
            'filter': 'license:"Creative Commons 0" duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'CC0 wind through leaves (60-120s)'
        },
        {
            'query': 'wind through trees',
            'filter': 'duration:[45 TO 90] tag:loop',
            'description': 'Wind through trees loops (45-90s)'
        },
    ],
    'crickets': [
        {
            'query': 'crickets',
            'filter': 'license:"Creative Commons 0" duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'CC0 cricket loops (60-120s)'
        },
        {
            'query': 'night crickets',
            'filter': 'duration:[45 TO 90] tag:loop',
            'description': 'Night cricket loops (45-90s)'
        },
        {
            'query': 'insects ambience',
            'filter': 'duration:[60 TO 120] (tag:seamless OR tag:loop)',
            'description': 'Insect ambience loops (60-120s)'
        },
    ],
}


class AmbientLoopSearcher:
    """Search Freesound for ambient nature loops."""

    def __init__(self):
        """Initialize searcher with Freesound client."""
        load_dotenv(Path(__file__).parent.parent / ".env")

        access_token = os.getenv("FREESOUND_ACCESS_TOKEN")
        if not access_token:
            raise ValueError(
                "No access token found. Run authentication first:\n"
                "  ./audio/download_freesound_library.py auth"
            )

        self.client = freesound.FreesoundClient()
        self.client.set_token(access_token, "oauth")

    def search_query(self, query: str, filter_str: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Execute a single search query.

        Args:
            query: Search query string
            filter_str: Filter string (Solr syntax)
            max_results: Maximum results to return

        Returns:
            List of sound metadata dicts
        """
        try:
            results = self.client.text_search(
                query=query,
                filter=filter_str,
                fields="id,name,username,duration,samplerate,bitdepth,license,tags,"
                       "avg_rating,num_ratings,num_downloads,num_comments,pack,description",
                page_size=min(max_results, 150),
                sort='rating_desc'  # Sort by rating (best first)
            )

            sounds = []
            for i, sound in enumerate(results):
                if i >= max_results:
                    break

                sounds.append({
                    'id': sound.id,
                    'name': sound.name,
                    'username': getattr(sound, 'username', 'unknown'),
                    'duration': getattr(sound, 'duration', None),
                    'samplerate': getattr(sound, 'samplerate', None),
                    'bitdepth': getattr(sound, 'bitdepth', None),
                    'license': getattr(sound, 'license', 'unknown'),
                    'tags': getattr(sound, 'tags', []),
                    'avg_rating': getattr(sound, 'avg_rating', None),
                    'num_ratings': getattr(sound, 'num_ratings', 0),
                    'num_downloads': getattr(sound, 'num_downloads', 0),
                    'num_comments': getattr(sound, 'num_comments', 0),
                    'pack': getattr(sound, 'pack', None),
                    'description': getattr(sound, 'description', '')[:200],  # First 200 chars
                    'url': f"https://freesound.org/s/{sound.id}/",
                })

            return sounds

        except Exception as e:
            print(f"  ✗ Search error: {e}")
            return []

    def search_category(self, category: str, max_per_query: int = 10, verbose: bool = False) -> Dict[str, Any]:
        """
        Search all queries for a category.

        Args:
            category: Category name (ocean, rain, forest, wind, crickets)
            max_per_query: Max results per query
            verbose: Print detailed results

        Returns:
            Dict with category results
        """
        if category not in SEARCH_QUERIES:
            raise ValueError(f"Unknown category: {category}")

        print(f"\n{'=' * 80}")
        print(f"CATEGORY: {category.upper()}")
        print(f"{'=' * 80}")

        category_results = {
            'category': category,
            'queries': []
        }

        for query_spec in SEARCH_QUERIES[category]:
            print(f"\n  Query: {query_spec['description']}")
            print(f"  Search: '{query_spec['query']}'")
            print(f"  Filter: {query_spec['filter']}")

            sounds = self.search_query(
                query_spec['query'],
                query_spec['filter'],
                max_per_query
            )

            print(f"  Results: {len(sounds)} sounds found")

            query_result = {
                'query': query_spec['query'],
                'filter': query_spec['filter'],
                'description': query_spec['description'],
                'count': len(sounds),
                'sounds': sounds
            }
            category_results['queries'].append(query_result)

            if verbose and sounds:
                print(f"\n  {'─' * 76}")
                for i, sound in enumerate(sounds[:5], 1):  # Show top 5
                    rating_str = f"{sound['avg_rating']:.1f}★" if sound['avg_rating'] else "N/A"
                    duration_str = f"{sound['duration']:.1f}s" if sound['duration'] else "?"
                    print(f"  [{i}] ID {sound['id']}: {sound['name']}")
                    print(f"      {rating_str} ({sound['num_ratings']} ratings) | "
                          f"{sound['num_downloads']} downloads | {duration_str} | "
                          f"{sound['license']}")
                    print(f"      Tags: {', '.join(sound['tags'][:8])}")
                    if sound.get('pack'):
                        print(f"      Pack: {sound['pack']}")
                    print()

        return category_results

    def search_all(self, max_per_query: int = 10, verbose: bool = False) -> List[Dict[str, Any]]:
        """
        Search all categories.

        Args:
            max_per_query: Max results per query
            verbose: Print detailed results

        Returns:
            List of category results
        """
        all_results = []

        for category in SEARCH_QUERIES.keys():
            category_results = self.search_category(category, max_per_query, verbose)
            all_results.append(category_results)

        return all_results

    def print_summary(self, results: List[Dict[str, Any]]):
        """Print summary statistics from search results."""
        print(f"\n{'=' * 80}")
        print("SEARCH SUMMARY")
        print(f"{'=' * 80}\n")

        total_queries = 0
        total_sounds = 0

        for category_result in results:
            category = category_result['category']
            num_queries = len(category_result['queries'])
            num_sounds = sum(q['count'] for q in category_result['queries'])

            total_queries += num_queries
            total_sounds += num_sounds

            print(f"  {category:12s}: {num_queries} queries, {num_sounds} sounds found")

        print(f"\n  {'─' * 76}")
        print(f"  {'TOTAL':12s}: {total_queries} queries, {total_sounds} sounds found")
        print(f"{'=' * 80}\n")

    def export_results(self, results: List[Dict[str, Any]], output_path: Path):
        """Export results to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Results exported to: {output_path}")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Search Freesound for ambient nature loops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--category',
        choices=list(SEARCH_QUERIES.keys()),
        help='Search specific category only (default: all)'
    )
    parser.add_argument(
        '--max-per-query',
        type=int,
        default=10,
        help='Maximum results per query (default: 10)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed results'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Export results to JSON file'
    )

    args = parser.parse_args()

    try:
        searcher = AmbientLoopSearcher()

        if args.category:
            results = [searcher.search_category(args.category, args.max_per_query, args.verbose)]
        else:
            results = searcher.search_all(args.max_per_query, args.verbose)

        searcher.print_summary(results)

        if args.output:
            searcher.export_results(results, args.output)

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
