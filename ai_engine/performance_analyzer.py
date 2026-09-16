def analyze_mcq_results(mcq_answers):
    weak_topics = []
    for topic, correct in mcq_answers.items():
        if correct < 50:  # <50% correct considered weak
            weak_topics.append(topic)
    return weak_topics