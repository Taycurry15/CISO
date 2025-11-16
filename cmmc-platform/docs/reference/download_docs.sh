#!/bin/bash
# CMMC Platform - Reference Documentation Download Script
# Downloads official NIST and CMMC documentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "==================================="
echo "CMMC Reference Documentation Downloader"
echo "==================================="
echo ""

# Function to download with retry
download_file() {
    local url=$1
    local output=$2
    local description=$3

    echo -e "${YELLOW}Downloading:${NC} $description"
    echo "  URL: $url"
    echo "  Output: $output"

    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$output")"

    # Try download with curl (3 retries)
    for i in {1..3}; do
        if curl -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
                --connect-timeout 30 \
                --max-time 300 \
                -o "$output" \
                "$url" 2>/dev/null; then

            # Check if file size is > 1KB (likely successful)
            if [ -f "$output" ] && [ $(stat -f%z "$output" 2>/dev/null || stat -c%s "$output" 2>/dev/null) -gt 1024 ]; then
                echo -e "${GREEN}✓ Success${NC} ($(du -h "$output" | cut -f1))"
                return 0
            else
                echo -e "${RED}✗ Download failed (file too small, likely access denied)${NC}"
                rm -f "$output"
            fi
        fi

        if [ $i -lt 3 ]; then
            echo "  Retrying in 2 seconds... (attempt $((i+1))/3)"
            sleep 2
        fi
    done

    echo -e "${RED}✗ Failed after 3 attempts${NC}"
    echo -e "${YELLOW}  → Manual download required. See README.md${NC}"
    return 1
}

echo "Downloading NIST Documentation..."
echo "-----------------------------------"

download_file \
    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf" \
    "nist/NIST.SP.800-171r2.pdf" \
    "NIST SP 800-171 Rev 2"

download_file \
    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171a.pdf" \
    "nist/NIST.SP.800-171A.pdf" \
    "NIST SP 800-171A"

echo ""
echo "Downloading CMMC Documentation..."
echo "-----------------------------------"

download_file \
    "https://dodcio.defense.gov/Portals/0/Documents/CMMC/ModelOverviewv2.pdf" \
    "cmmc/CMMC-Model-v2.13.pdf" \
    "CMMC Model v2.13"

download_file \
    "https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf" \
    "cmmc/CMMC-AssessmentGuide-L2-v2.13.pdf" \
    "CMMC Assessment Guide L2 v2.13"

download_file \
    "https://dodcio.defense.gov/Portals/0/Documents/CMMC/ScopingGuideL2v2.pdf" \
    "cmmc/CMMC-ScopingGuide-L2-v2.13.pdf" \
    "CMMC Scoping Guide L2 v2.13"

download_file \
    "https://dodcio.defense.gov/Portals/0/Documents/CMMC/Scope_Level2_V2.0_FINAL_20211202_508.pdf" \
    "cmmc/CMMC-Scope-L2-v2.0.pdf" \
    "CMMC Scope L2 v2.0"

echo ""
echo "Downloading Additional Guides (Optional)..."
echo "-----------------------------------"

download_file \
    "https://www.acq.osd.mil/asda/dpc/cp/cyber/docs/safeguarding/NIST-SP-800-171-Assessment-Methodology-Version-1.2.1-6.24.2020.pdf" \
    "guides/NIST-SP-800-171-DoD-Assessment-Methodology.pdf" \
    "DoD Assessment Methodology"

download_file \
    "https://download.microsoft.com/download/c/a/6/ca67ab87-4832-476e-8f01-b1572c7a740c/Microsoft%20Technical%20Reference%20Guide%20for%20CMMC%20v2_(Public%20Preview)_20220304%20(2).pdf" \
    "guides/Microsoft-CMMC-2.0-Technical-Reference.pdf" \
    "Microsoft CMMC 2.0 Guide"

echo ""
echo "==================================="
echo "Download Summary"
echo "==================================="

# Count successful downloads
NIST_COUNT=$(find nist -name "*.pdf" -size +1k 2>/dev/null | wc -l)
CMMC_COUNT=$(find cmmc -name "*.pdf" -size +1k 2>/dev/null | wc -l)
GUIDE_COUNT=$(find guides -name "*.pdf" -size +1k 2>/dev/null | wc -l)
TOTAL=$((NIST_COUNT + CMMC_COUNT + GUIDE_COUNT))

echo "NIST Documents: $NIST_COUNT"
echo "CMMC Documents: $CMMC_COUNT"
echo "Additional Guides: $GUIDE_COUNT"
echo "-----------------------------------"
echo "Total: $TOTAL documents"

if [ $TOTAL -gt 0 ]; then
    echo ""
    echo -e "${GREEN}Download complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Verify documents: ls -lh nist/ cmmc/ guides/"
    echo "2. Ingest into RAG: python scripts/ingest_reference_docs.py"
    echo "3. Check status: python scripts/ingest_reference_docs.py --status"
else
    echo ""
    echo -e "${RED}No documents downloaded successfully.${NC}"
    echo ""
    echo "This is likely due to access restrictions on government sites."
    echo "Please download documents manually following the README.md instructions."
fi

echo ""
