# Version 1 – simple momentum (will be replaced by Perplexity suggestions)
def score_coin(return_24h, return_6h, volume_ratio, news_sentiment):
    return (
        0.5 * return_24h +
        0.3 * return_6h +
        0.15 * volume_ratio +
        0.05 * news_sentiment
    )

