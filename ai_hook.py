def process_with_ai(tweet):
    """
    Entrée: tweet dict {tweet_id, author, text, link}
    Sortie:
      - None / False => ignorer
      - string => texte final à poster
    """
    text = tweet.get('text', '')
    author = tweet.get('author', '')
    # Simule décision IA : filtrage football/mercato
    if "football" in text.lower() or "mercato" in text.lower():
        return f"[INFO] {text[:240]} @{author} Que penses-tu ?"
    return None
