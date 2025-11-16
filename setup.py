from setuptools import setup, find_packages

setup(
    name="llm_analysis_quiz",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "playwright>=1.32.0",
        "python-dotenv>=0.19.0",
        "pydantic>=1.8.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.28.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "python-magic>=0.4.27",
    ],
    python_requires=">=3.9",
)