#!/bin/bash
# One script to rule them all

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f "secrets.env" ]; then
    export $(cat secrets.env | grep -v '^#' | xargs)
fi

# Determine Python command
PYTHON_CMD="python3"
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

# Run the specified module
case "$1" in
    fetch_data)
        $PYTHON_CMD src/01_fetch_data.py
        ;;
    sentiment)
        $PYTHON_CMD src/02_sentiment.py
        ;;
    predict_and_trade)
        $PYTHON_CMD src/03_predict_and_trade.py
        ;;
    sell_position)
        $PYTHON_CMD src/06_sell_position.py
        ;;
    record_results)
        $PYTHON_CMD src/04_record_results.py
        ;;
    self_improve)
        $PYTHON_CMD src/05_self_improve.py
        ;;
    self_analyze)
        $PYTHON_CMD src/07_self_analyze.py
        ;;
    backtest)
        $PYTHON_CMD backtest.py
        ;;
    *)
        echo "Usage: $0 {fetch_data|sentiment|predict_and_trade|sell_position|record_results|self_improve|self_analyze|backtest}"
        exit 1
        ;;
esac

