from setuptools import setup, find_packages

setup(
    name="fede_crawl4ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "beautifulsoup4>=4.12",
        "pillow>=10.4",
        "pydantic>=2.10",
        "rich>=13.9.4",
    ],
    python_requires=">=3.8",
) 