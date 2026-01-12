# Contributing

We welcome contributions to NegMAS App! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Clone and Install

```bash
git clone https://github.com/yasserfarouk/negmas-app.git
cd negmas-app

# Install with development dependencies
uv sync
uv pip install -e ".[dev,docs]"
```

### Running the Development Server

```bash
uv run negmas-app --debug
```

## Project Structure

```
negmas-app/
├── negmas_app/           # Main package
│   ├── models/           # Data models (dataclasses)
│   ├── routers/          # FastAPI route handlers
│   ├── services/         # Business logic
│   ├── static/           # CSS, JS, images
│   │   ├── css/
│   │   └── js/
│   └── templates/        # Jinja2 templates
├── scenarios/            # Bundled negotiation scenarios
├── tests/                # Test suite
├── docs/                 # Documentation (MkDocs)
└── pyproject.toml        # Project configuration
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=negmas_app

# Run specific test file
uv run pytest tests/test_routes.py -v
```

## Type Checking

```bash
uv run pyright negmas_app/
```

## Documentation

### Building Docs Locally

```bash
# Install docs dependencies
uv pip install -e ".[docs]"

# Serve docs locally
uv run mkdocs serve
```

Docs will be available at http://127.0.0.1:8000

### Writing Documentation

- Documentation is in `docs/` directory
- Use [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) features
- Follow existing structure and style

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Your Changes

- Follow the code style guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Run Checks

```bash
# Run tests
uv run pytest

# Type check
uv run pyright negmas_app/

# Build docs
uv run mkdocs build
```

### 4. Commit and Push

```bash
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

### 5. Create Pull Request

Open a pull request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots (for UI changes)

## Code Style

### Python

- Use type hints on all functions
- Use `@dataclass` for data models
- Prefer explicit over implicit
- Use `if x is None:` instead of `if not x:`

### JavaScript

- Use modern ES6+ syntax
- Document functions with JSDoc comments
- Follow existing patterns in the codebase

### CSS

- Use CSS variables for theming
- Follow BEM naming convention
- Mobile-first responsive design

## Architecture Guidelines

### Backend (Python)

- **models/**: Pure dataclasses, no business logic
- **services/**: Business logic, no HTTP concerns
- **routers/**: HTTP handlers, minimal logic

### Frontend (JavaScript)

- **Alpine.js**: Reactive state management
- **HTMX**: Server interactions
- **Plotly.js**: Charts and visualizations

## Questions?

- Open an issue on GitHub
- Check existing issues and PRs
