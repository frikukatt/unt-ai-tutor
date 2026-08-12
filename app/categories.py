from fastapi import APIRouter

router = APIRouter()


ENT_CATEGORIES = [
    {
        "id": 1,
        "name": "Computer Science",
        "code": "computer-science"
    },
    {
        "id": 2,
        "name": "Mathematics",
        "code": "mathematics"
    },
    {
        "id": 3,
        "name": "Physics",
        "code": "physics"
    },
    {
        "id": 4,
        "name": "Chemistry",
        "code": "chemistry"
    },
    {
        "id": 5,
        "name": "Biology",
        "code": "biology"
    },
    {
        "id": 6,
        "name": "Geography",
        "code": "geography"
    },
    {
        "id": 7,
        "name": "World History",
        "code": "world-history"
    },
    {
        "id": 8,
        "name": "Political Science",
        "code": "political-science"
    },
    {
        "id": 9,
        "name": "English",
        "code": "english"
    },
    {
        "id": 10,
        "name": "Kazakh Language",
        "code": "kazakh-language"
    },
    {
        "id": 11,
        "name": "Russian Language",
        "code": "russian-language"
    },
    {
        "id": 12,
        "name": "Literature",
        "code": "literature"
    },
    {
        "id": 13,
        "name": "Reading Literacy",
        "code": "reading-literacy"
    },
    {
        "id": 14,
        "name": "Mathematical Literacy",
        "code": "mathematical-literacy"
    },
    {
        "id": 15,
        "name": "History of Kazakhstan",
        "code": "history-kazakhstan"
    },
    {
        "id": 16,
        "name": "Creative Exam 1",
        "code": "creative-exam-1"
    },
    {
        "id": 17,
        "name": "Creative Exam 2",
        "code": "creative-exam-2"
    }
]


@router.get("/categories")
def get_categories():
    return ENT_CATEGORIES