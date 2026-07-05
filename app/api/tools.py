"""GET /api/tools — статический список плиток инструментов (LND-4).

Public endpoint для shell'а на raftforge.art. SPA рисует иконки — клик
ведёт на сабдомен инструмента, там свой auth-check (401 если нет).

Список меняется через edit + rebuild контейнера. Плитки меняются
редко, deploy pipeline через `docker compose up -d --build` достаточен.
"""
from fastapi import APIRouter

router = APIRouter()


TOOLS = [
    {
        "key": "notes",
        "title": "Заметки",
        "icon": "📝",
        "url": "https://notes.dev.raftforge.art/",
        "resource": "notes-dev",
        "min_level": 200,
    },
    {
        "key": "diary",
        "title": "Дневник",
        "icon": "📔",
        "url": "https://diary.dev.raftforge.art/",
        "resource": "diary-dev",
        "min_level": 200,
    },
    {
        "key": "board",
        "title": "Доска",
        "icon": "🎨",
        "url": "https://board.dev.raftforge.art/",
        "resource": "board-dev",
        "min_level": 200,
    },
    {
        "key": "docs",
        "title": "Документы",
        "icon": "📚",
        "url": "https://docs.dev.raftforge.art/",
        "resource": "docs-dev",
        "min_level": 200,
    },
    {
        "key": "tasks",
        "title": "Задачи",
        "icon": "✅",
        "url": "https://tasks.dev.raftforge.art/",
        "resource": "tasks-dev",
        "min_level": 200,
    },
]


@router.get("/api/tools")
def tools_list():
    return TOOLS
