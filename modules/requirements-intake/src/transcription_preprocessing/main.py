import argparse
import sys
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Add project root to sys.path if needed
current_path = Path(__file__).resolve().parent
project_root = current_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from transcription_preprocessing.processor import TranscriptionProcessor

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Process transcriptions to generate PRD.")
    parser.add_argument("transcript_path", type=str, help="Path to the transcript file.")
    parser.add_argument("--output", "-o", type=str, help="Output file path for the PRD.", default=None)
    
    args = parser.parse_args()
    
    transcript_path = Path(args.transcript_path)
    if not transcript_path.exists():
        logger.error(f"Transcript file not found: {transcript_path}")
        sys.exit(1)
        
    logger.info(f"Reading transcript from {transcript_path}")
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        sys.exit(1)
        
    processor = TranscriptionProcessor()

    
    try:
        import json
        prd = processor.process_transcript(transcript_text)
        # prd = {"PingoLePongo": "PongolePingo", "PongoLePingo": 69}
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(prd, f, indent=4)
            logger.info(f"PRD saved to {output_path}")
        else:
            print("\n" + "="*80)
            print("GENERATED PRD")
            print("="*80 + "\n")
            print(prd)
            print("\n" + "="*80)
            
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        logger.info(f"Printing PRD: \n {prd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
