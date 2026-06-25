from setuptools import setup, find_packages

setup(
    name="extrator_vestibulares_api",
    version="1.0.0",
    description="API programática e REST (FastAPI) para extração de provas e gabaritos de vestibulares (1ª e 2ª Fase).",
    author="Desenvolvedor",
    # Encontra e empacota automaticamente os módulos do diretório
    packages=find_packages(),
    py_modules=["extratorUNICAMP", "models", "processor", "extractor", "saver", "app"],
    python_requires=">=3.8",
    # Dependências obrigatórias que serão instaladas automaticamente
    install_requires=[
        "pymupdf>=1.22.0",
        "pillow>=9.0.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "python-multipart>=0.0.6",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
