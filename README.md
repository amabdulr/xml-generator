# DITA XML Generator

A Streamlit app for generating Cisco DITA XML files from templates. Create concepts, tasks, processes, principles, and references — then bundle them into a chapter map and download as a zip.

## Features

- Generate DITA XML files from predefined templates (concept, task, process, principle, reference)
- Automatically applies proper naming conventions (kebab-case IDs, type prefixes like `c-`, `t-`, `pr-`, etc.)
- Create chapter maps (`.ditamap`) that organize generated files by type
- Upload and incorporate your own XML files alongside generated ones
- Download all files as a zip

## Setup

```bash
pip install -r requirements.txt
streamlit run xml_generator.py
```

## Project Structure

```
xml_generator.py       # Main Streamlit app
templates/             # DITA XML templates
  ct-concept.xml
  ct-task.xml
  ct-process.xml
  ct-principle.xml
  ct-reference.xml
  chaptermap.ditamap
requirements.txt       # Dependencies (streamlit)
```