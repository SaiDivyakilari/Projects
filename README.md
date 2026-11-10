# GenAI and Agentic AI Projects

Welcome to the **GenAI and Agentic AI Projects** repository. This monorepo houses multiple independent projects showcasing the use of generative AI, large language models (LLMs), and agentic workflows. Each sub‑directory contains a self‑contained application with its own README, requirements, and usage instructions.

---

## 📚 Repository Overview

| Project | Description | Primary Tech |
|---------|-------------|--------------|
| **ai‑workout‑plan‑generator** | A Streamlit web app that generates personalized weekly workout plans using an LLM via the Groq API. | Streamlit, Groq LLM, Python |
| **medibot‑assistant** | A medical‑assistant chatbot that answers clinical queries, performs text‑to‑SQL retrieval‑augmented generation, and includes various medical reference documents. | FastAPI, LangChain, SQLite, Streamlit |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+**
- **Git**
- (Optional) **virtualenv** or **conda** for isolated environments
- An API key for the Groq LLM (required for the workout‑plan generator)

### Clone the Repository

```bash
git clone https://github.com/<your‑username>/<repo‑name>.git
cd <repo‑name>
```

### Set Up a Project

Each project lives in its own folder. Follow the steps below for the project you want to run.

#### 1️⃣ AI Workout Plan Generator

```bash
cd ai-workout-plan-generator
python -m venv .venv   # or conda create -n workout python=3.9
source .venv/bin/activate   # on Windows use .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file (or export the variable) with your Groq API key:

```text
GROQ_API_KEY=your_groq_api_key_here
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Open the displayed URL (usually `http://localhost:8501`) in your browser.

#### 2️⃣ Medibot Assistant

```bash
cd ../medibot-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The assistant uses a local SQLite database (`mediassist.db`). Ensure the `Data/` folder is present (it is shipped with the repo).

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive API documentation, or launch the optional Streamlit UI:

```bash
streamlit run streamlit_app.py
```

---

## 📖 Usage Guide

### AI Workout Plan Generator

1. **Enter your fitness goals** (e.g., strength, endurance, weight loss).
2. **Select preferred equipment** (dumbbells, bodyweight, etc.).
3. Click **Generate** – the LLM crafts a 7‑day plan with sets, reps, and rest periods.
4. Export the plan as a PDF via the *Download* button.

### Medibot Assistant

- **Ask clinical questions** via the `/chat` endpoint or the Streamlit UI.
- **Perform text‑to‑SQL queries** using the `/rag` endpoint, which retrieves relevant records from the medical database.
- The bot references PDFs in the `Data/` folder for factual grounding.

---

## 🤝 Contributing

Contributions are welcome! Follow these steps:

1. **Fork** the repository.
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and ensure the code passes linting and tests (if applicable).
4. **Commit** with a clear message:
   ```bash
   git commit -m "feat: brief description of the change"
   ```
5. **Push** to your fork and open a Pull Request against `main`.

### Pull Request Checklist

- [ ] Documentation updated (README, inline docs, etc.)
- [ ] Code style follows the existing conventions (PEP 8 for Python)
- [ ] New dependencies are added to the appropriate `requirements.txt`
- [ ] Tests added/updated (if the project has a test suite)

---

## 📄 License

This repository is licensed under the **MIT License** – see the `LICENSE` file for details.

---

## 📬 Contact

For questions or feedback, please open an issue or reach out to the repository maintainers.

---

*Happy coding!*
