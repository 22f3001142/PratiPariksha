from collections import defaultdict
from statistics import mean

from .models import Forum, Question, Resource, Response, Student, Teacher


def normalize_answer(value):
    if value is None:
        return ''
    return str(value).strip().lower()


def is_correct(question, answer):
    if question is None:
        return False
    if question.type == 'MSQ':
        actual = sorted([item.strip().lower() for item in str(answer or '').split(',') if item.strip()])
        expected = sorted([item.strip().lower() for item in str(question.correct_answer or '').split(',') if item.strip()])
        return actual == expected
    return normalize_answer(question.correct_answer) == normalize_answer(answer)


def topic_label(question):
    topic = question.topic or 'General'
    subtopic = question.subtopic or 'General'
    if subtopic and subtopic != topic:
        return f"{topic} / {subtopic}"
    return topic


def build_student_snapshot(student_id):
    student = Student.query.get(student_id)
    if not student:
        return None

    responses = (
        Response.query.join(Question, Response.question_id == Question.id)
        .filter(Response.student_id == student_id)
        .all()
    )
    total_questions = Question.query.count()
    correct = 0
    topic_stats = defaultdict(lambda: {'correct': 0, 'attempted': 0})
    recent_topics = []

    for response in responses:
        question = Question.query.get(response.question_id)
        if not question:
            continue
        label = topic_label(question)
        topic_stats[label]['attempted'] += 1
        if is_correct(question, response.answer):
            correct += 1
            topic_stats[label]['correct'] += 1
        recent_topics.append(label)

    attempted = len(responses)
    accuracy = round((correct / attempted) * 100, 2) if attempted else 0.0
    weak_topics = []
    for label, stats in topic_stats.items():
        topic_accuracy = (stats['correct'] / stats['attempted']) if stats['attempted'] else 0
        if topic_accuracy < 0.7:
            weak_topics.append({
                'topic': label,
                'accuracy': round(topic_accuracy * 100, 2),
                'attempted': stats['attempted']
            })
    weak_topics.sort(key=lambda item: (item['accuracy'], item['attempted']))
    weak_topics = weak_topics[:3]

    if weak_topics:
        improvement_areas = [
            f"Rework {topic['topic']} because current accuracy is {topic['accuracy']}%."
            for topic in weak_topics
        ]
    elif attempted:
        improvement_areas = [
            'Keep revising mixed-topic timed sets to convert good accuracy into faster completion.'
        ]
    else:
        improvement_areas = [
            'Start with a diagnostic test so the system can identify your strongest and weakest topics.'
        ]

    study_plan = build_study_plan(student, weak_topics, attempted, total_questions)

    return {
        'student_id': student.admission_id,
        'student_name': student.name,
        'marks': correct,
        'attempted': attempted,
        'accuracy': accuracy,
        'ability_estimate': round(correct / total_questions, 2) if total_questions else 0,
        'weak_topics': weak_topics,
        'improvement_areas': improvement_areas,
        'study_plan': study_plan,
        'points': student.points,
        'level': student.level,
    }


def build_study_plan(student, weak_topics, attempted, total_questions):
    if not attempted:
        return [
            'Take the next available test to generate your first performance baseline.',
            'Review the starter question bank topic by topic beginning with Arithmetic and Algebra.',
            'Ask one doubt in the discussion forum after every study session to keep feedback loops short.'
        ]

    plan = []
    for weak_topic in weak_topics[:3]:
        plan.append(
            f"Spend 25 minutes on {weak_topic['topic']} and then solve 5 targeted questions immediately after revision."
        )

    if not plan:
        plan.append('Attempt one mixed timed quiz every day to preserve momentum across all topics.')

    plan.append(
        f"Review every incorrect response from your {attempted} attempted question(s) and write a one-line correction note."
    )
    plan.append(
        'Use the study bot for concept recap, then post unresolved doubts in the forum so your teacher can respond.'
    )
    return plan[:4]


def build_teacher_analytics(teacher_id=None):
    teacher = Teacher.query.get(teacher_id) if teacher_id else None
    teacher_subject = (teacher.subject or 'Mathematics') if teacher else None

    student_query = Student.query
    if teacher_id:
        student_query = student_query.filter_by(assigned_teacher_id=teacher_id)
    students = student_query.all()

    question_query = Question.query
    if teacher_subject:
        question_query = question_query.filter_by(topic=teacher_subject)
    question_rows = question_query.all()
    question_count = len(question_rows)
    snapshots = [build_student_snapshot(student.admission_id) for student in students]
    snapshots = [snapshot for snapshot in snapshots if snapshot is not None]

    avg_marks = round(mean([snapshot['marks'] for snapshot in snapshots]), 2) if snapshots else 0
    avg_accuracy = round(mean([snapshot['accuracy'] for snapshot in snapshots]), 2) if snapshots else 0

    topic_totals = defaultdict(lambda: {'correct': 0, 'attempted': 0})
    irt_analysis = []
    for question in question_rows:
        question_responses = Response.query.filter_by(question_id=question.id).all()
        if not question_responses:
            irt_analysis.append({
                'question_id': question.id,
                'question': question.question,
                'topic': question.topic or 'General',
                'subtopic': question.subtopic or question.topic or 'General',
                'topic_label': topic_label(question),
                'difficulty_index': 0,
                'discrimination_index': 0,
            })
            continue

        correctness = [1 if is_correct(question, response.answer) else 0 for response in question_responses]
        difficulty_index = round(sum(correctness) / len(correctness), 2)

        student_scores = {}
        for response in question_responses:
            snapshot = next((item for item in snapshots if item['student_id'] == response.student_id), None)
            if snapshot:
                student_scores[response.student_id] = snapshot['marks']

        top_group = []
        bottom_group = []
        if student_scores:
            ordered = sorted(student_scores.items(), key=lambda item: item[1], reverse=True)
            cutoff = max(1, len(ordered) // 2)
            top_ids = {student_id for student_id, _ in ordered[:cutoff]}
            bottom_ids = {student_id for student_id, _ in ordered[-cutoff:]}
            for response in question_responses:
                mark = 1 if is_correct(question, response.answer) else 0
                if response.student_id in top_ids:
                    top_group.append(mark)
                if response.student_id in bottom_ids:
                    bottom_group.append(mark)

        discrimination_index = round((mean(top_group) if top_group else 0) - (mean(bottom_group) if bottom_group else 0), 2)
        irt_analysis.append({
            'question_id': question.id,
            'question': question.question,
            'topic': question.topic or 'General',
            'subtopic': question.subtopic or question.topic or 'General',
            'topic_label': topic_label(question),
            'difficulty_index': difficulty_index,
            'discrimination_index': discrimination_index,
        })

    for snapshot in snapshots:
        for weak_topic in snapshot['weak_topics']:
            topic_totals[weak_topic['topic']]['attempted'] += weak_topic['attempted']
            topic_totals[weak_topic['topic']]['correct'] += (weak_topic['accuracy'] / 100) * weak_topic['attempted']

    weak_topics = []
    for label, stats in topic_totals.items():
        accuracy = (stats['correct'] / stats['attempted']) if stats['attempted'] else 0
        weak_topics.append({
            'topic': label,
            'accuracy': round(accuracy * 100, 2),
            'attempted': stats['attempted']
        })
    weak_topics.sort(key=lambda item: (item['accuracy'], -item['attempted']))

    if not weak_topics and question_count:
        question_topics = sorted({topic_label(question) for question in question_rows})
        weak_topics = [{'topic': topic, 'accuracy': 0, 'attempted': 0} for topic in question_topics[:3]]

    return {
        'avg_marks': avg_marks,
        'avg_accuracy': avg_accuracy,
        'weak_topics': weak_topics[:5],
        'irt_analysis': irt_analysis,
        'student_abilities': snapshots,
        'subject': teacher_subject or 'All Subjects',
    }


def build_forum_payload(teacher_id=None):
    posts = Forum.query.order_by(Forum.id.desc()).all()
    result = []
    for post in posts:
        student = Student.query.get(post.student_id)
        if teacher_id and student and student.assigned_teacher_id != teacher_id:
            continue
        result.append({
            'id': post.id,
            'student_name': student.name if student else 'Unknown',
            'student_id': post.student_id,
            'post': post.post,
            'reply': post.reply,
            'poll': post.poll,
            'vote': post.vote,
        })
    return result


def generate_study_bot_reply(student_id, query):
    snapshot = build_student_snapshot(student_id)
    lowered_query = (query or '').strip().lower()
    if snapshot is None:
        return {
            'reply': 'I could not find your learner profile yet. Please sign in again and retry.',
            'suggestions': []
        }
    student = Student.query.get(student_id)
    teacher = Teacher.query.get(student.assigned_teacher_id) if student and student.assigned_teacher_id else None
    resource_query = Resource.query
    question_query = Question.query
    if teacher and teacher.subject:
        resource_query = resource_query.filter_by(topic=teacher.subject)
        question_query = question_query.filter_by(topic=teacher.subject)
    resources = resource_query.all()
    questions = question_query.all()
    matching_resources = [
        resource for resource in resources
        if lowered_query and (
            lowered_query in resource.title.lower() or lowered_query in (resource.topic or '').lower()
        )
    ]
    matching_questions = [
        question for question in questions
        if lowered_query and (
            lowered_query in question.question.lower()
            or lowered_query in (question.topic or '').lower()
            or lowered_query in (question.subtopic or '').lower()
        )
    ]

    if matching_resources:
        first = matching_resources[0]
        return {
            'reply': f"Start with the resource '{first.title}' for {first.topic}. After that, solve 3 questions on the same topic to lock in the concept.",
            'suggestions': [item.title for item in matching_resources[:3]]
        }

    if matching_questions:
        first = matching_questions[0]
        explanation = first.explanation or f"Review why the correct answer is '{first.correct_answer}'."
        return {
            'reply': f"I found a related question in {topic_label(first)}. {explanation}",
            'suggestions': [question.question for question in matching_questions[:2]]
        }

    if snapshot['weak_topics']:
        focus_topic = snapshot['weak_topics'][0]['topic']
        return {
            'reply': f"Your biggest improvement area right now is {focus_topic}. Spend one short session revising the concept, then try a timed mini-set and bring any stuck point to the forum.",
            'suggestions': snapshot['study_plan']
        }

    return {
        'reply': 'You are in a good place to continue mixed practice. Ask me about a topic, a formula, or a question you got wrong, and I will point you to the best next step.',
        'suggestions': snapshot['study_plan']
    }
