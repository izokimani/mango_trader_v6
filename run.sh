#!/bin/bash
# One script to rule them all

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
export $(cat secrets.env | grep -v '^#' | xargs)

# Run the specified module
case "$1" in
    fetch_data)
        python src/01_fetch_data.py
        ;;
    sentiment)
        python src/02_sentiment.py
        ;;
    predict_and_trade)
        python src/03_predict_and_trade.py
        ;;
    sell_position)
        python src/06_sell_position.py
        ;;
    record_results)
        python src/04_record_results.py
        ;;
    self_improve)
        python src/05_self_improve.py
        ;;
    self_analyze)
        python src/07_self_analyze.py
        ;;
    backtest)
        python backtest.py
        ;;
    *)
        echo "Usage: $0 {fetch_data|sentiment|predict_and_trade|sell_position|record_results|self_improve|self_analyze|backtest}"
        exit 1
        ;;
esac

