#!/usr/bin/env python3
"""Entry point for the daily Reddit content automation pipeline."""

import sys
import traceback
from pathlib import Path

# Add project src to path
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_ROOT))

from reddit_automation.pipeline.run_daily import run_daily_pipeline


def main():
    """Run the pipeline and report results."""
    print("=" * 60)
    print("Reddit Content Automation - Daily Pipeline")
    print("=" * 60)
    
    try:
        result = run_daily_pipeline()
        print(f"\nPipeline completed successfully!")
        print(f"Status: {result.get('status', 'unknown')}")
        if 'title' in result:
            print(f"Title: {result['title']}")
        if 'video_path' in result:
            print(f"Video: {result['video_path']}")
        if 'publish_result' in result:
            print(f"Published: {result['publish_result']}")
        return 0
        
    except Exception as exc:
        print(f"\nPipeline failed with error:")
        print(f"  {exc.__class__.__name__}: {exc}")
        print("\nFull traceback:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
