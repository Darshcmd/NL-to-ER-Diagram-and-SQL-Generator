# Architecture

SchemaFlow is organized as a two-layer application:

- `frontend/` renders the guided user flow and displays diagrams, SQL, validation notes, and chat history
- `backend/` handles session state, file ingestion, schema generation, Mermaid rendering, and SQL generation

## Request Flow

```mermaid
flowchart LR
    User[User] --> Input[InputPhase]
    Input --> Init[POST /api/chat/init]
    Init --> Questions[Clarifying questions]
    Questions --> Confirm[POST /api/chat/confirm-answers]
    Confirm --> Diagram[Mermaid ER diagram]
    Diagram --> Refine[POST /api/chat/refine]
    Refine --> Diagram
    Diagram --> SQL[POST /api/chat/generate-sql]
    SQL --> Viewer[SQLViewer]
```

## Frontend Blocks

```mermaid
flowchart TB
    subgraph App Shell
        MainApp[MainApp.jsx]
        SchemaContext[SchemaContext.jsx]
    end

    subgraph Input Stage
        InputPhase[InputPhase.jsx]
        QuestionsPhase[QuestionsPhase.jsx]
    end

    subgraph Output Stage
        MermaidDiagram[MermaidDiagram.jsx]
        ValidationPanel[ValidationPanel.jsx]
        RefinementPhase[RefinementPhase.jsx]
        SQLViewer[SQLViewer.jsx]
        ChatHistory[ChatHistory.jsx]
    end

    MainApp --> InputPhase
    MainApp --> QuestionsPhase
    MainApp --> MermaidDiagram
    MainApp --> ValidationPanel
    MainApp --> RefinementPhase
    MainApp --> SQLViewer
    MainApp --> ChatHistory
    InputPhase --> SchemaContext
    QuestionsPhase --> SchemaContext
    RefinementPhase --> SchemaContext
    MermaidDiagram --> SchemaContext
    SQLViewer --> SchemaContext
```

## Backend Blocks

```mermaid
flowchart TB
    subgraph HTTP Layer
        ChatRoutes[backend/app/routes/chat.py]
        FileRoutes[backend/app/routes/files.py]
        SchemaRoutes[backend/app/routes/schema.py]
    end

    subgraph Core Services
        GeminiService[backend/app/services/gemini_service.py]
        SessionStore[backend/app/services/session_manager.py]
        FileProcessor[backend/app/utils/file_processor.py]
    end

    ChatRoutes --> GeminiService
    ChatRoutes --> SessionStore
    FileRoutes --> FileProcessor
    FileRoutes --> GeminiService
    SchemaRoutes --> GeminiService
    GeminiService --> SessionStore
```

## Why The Repo Is Structured This Way

- The frontend owns the UX state and stage transitions
- The backend owns generation and validation logic, so the diagram output stays consistent
- Session state is isolated so each project flow can be refined independently
- Mermaid output is kept as the source of truth, which makes export and regeneration straightforward

## Files Worth Knowing

- [backend/main.py](../backend/main.py) registers the FastAPI app and routers
- [backend/app/routes/chat.py](../backend/app/routes/chat.py) drives the guided schema flow
- [backend/app/services/gemini_service.py](../backend/app/services/gemini_service.py) renders Mermaid and SQL
- [frontend/src/components/MainApp.jsx](../frontend/src/components/MainApp.jsx) chooses which stage to show
- [frontend/src/components/MermaidDiagram.jsx](../frontend/src/components/MermaidDiagram.jsx) renders the SVG output
- [frontend/src/utils/api.js](../frontend/src/utils/api.js) centralizes API calls

## Notes

- Mermaid diagrams are rendered in the frontend, but the backend generates the actual diagram text
- The schema payload is embedded in Mermaid comments so the app can preserve structure across regeneration
- File upload support is intentionally lightweight so the text extraction layer stays easy to reason about
