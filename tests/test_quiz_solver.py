import pytest
from unittest.mock import patch, MagicMock
from src.quiz_solver import QuizSolver, QuizQuestion

class TestQuizSolver:
    def test_initialization(self, sample_quiz_data):
        """Test that QuizSolver initializes with the correct data."""
        solver = QuizSolver(sample_quiz_data)
        assert solver.quiz_data == sample_quiz_data
        assert isinstance(solver.questions, list)

    def test_solve_question_multiple_choice(self):
        """Test solving a multiple choice question."""
        question = QuizQuestion(
            question_id="q1",
            question_text="What is the capital of France?",
            question_type="multiple_choice",
            options=["London", "Paris", "Berlin", "Madrid"]
        )
        solver = QuizSolver({})
        answer = solver._solve_question(question)
        assert answer in question.options

    def test_solve_question_number(self):
        """Test solving a number question."""
        question = QuizQuestion(
            question_id="q2",
            question_text="What is 2+2?",
            question_type="number"
        )
        solver = QuizSolver({})
        with patch('random.randint', return_value=4):
            answer = solver._solve_question(question)
            assert answer == 4

    def test_solve_all_questions(self, sample_quiz_data):
        """Test solving all questions in a quiz."""
        solver = QuizSolver(sample_quiz_data)
        with patch.object(solver, '_solve_question') as mock_solve:
            mock_solve.side_effect = ["Paris", 4]
            answers = solver.solve_all()
            
            assert len(answers) == 2
            assert answers[0] == {"id": "q1", "answer": "Paris"}
            assert answers[1] == {"id": "q2", "answer": 4}

    def test_generate_quiz_report(self, sample_quiz_questions):
        """Test generating a quiz report."""
        solver = QuizSolver({})
        solver.questions = sample_quiz_questions
        
        report = solver.generate_report()
        
        assert "total_questions" in report
        assert report["total_questions"] == 2
        assert "answers" in report
        assert len(report["answers"]) == 2
