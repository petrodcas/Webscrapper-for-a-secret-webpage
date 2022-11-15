import json
# It ignores questions that have any kind of images
if __name__ == '__main__':
    json_file = '.\questions.json'
    out_file = '.\questions.txt'
    question_format = 'Question #%d\n---\n%s\n-----\nAnswers:\n%s\n-----\nCorrect answer: %s\n-----\nExplanation:\n %s\n\n______________________________________________\n\n'

    questions = None

    with open(json_file, mode='r', encoding='utf-8') as f:
        questions = json.load(f)
    
    with open(out_file, mode='w', encoding='utf-8') as f:
        lines = [question_format%(
                    int(q['id']), 
                    q['formulation'], 
                    '\n'.join(['- %s'%answer for answer in q['answers']]),
                    q['correct_answer'],
                    q['explanation']
                ) for q in questions if not len(q['correct_answer_images']) or not len(q['formulation_images'])]
        
        f.writelines(lines)
    
