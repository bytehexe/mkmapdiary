# Task Dependencies

This document shows the dependency graph of the various build tasks in mkmapdiary. The tasks are organized in a directed acyclic graph (DAG) where arrows indicate dependencies.

```plantuml
@startuml task-dependencies

' Directory creation tasks (foundational)
rectangle "create_directory" as create_dir #lightblue

' Data conversion tasks
rectangle "geo2gpx" as geo2gpx #lightgreen
rectangle "qstarz2gpx" as qstarz2gpx #lightgreen
rectangle "convert_raw" as convert_raw #lightgreen
rectangle "convert_image" as convert_image #lightgreen
rectangle "convert_audio" as convert_audio #lightgreen
rectangle "text2markdown" as text2markdown #lightgreen
rectangle "markdown2markdown" as markdown2markdown #lightgreen

' GPX processing tasks
rectangle "pre_gpx" as pre_gpx #yellow
rectangle "geo_correlation" as geo_correlation #yellow
rectangle "gpx2gpx" as gpx2gpx #orange
rectangle "get_gpx_deps" as get_gpx_deps #orange

' Content generation tasks
rectangle "transcribe_audio" as transcribe_audio #pink
rectangle "build_day_page" as build_day_page #lightcyan
rectangle "build_gallery" as build_gallery #lightcyan
rectangle "build_journal" as build_journal #lightcyan
rectangle "build_tags" as build_tags #lightcyan

' Site building tasks
rectangle "generate_mkdocs_config" as generate_mkdocs_config #lavender
rectangle "build_static_pages" as build_static_pages #lavender
rectangle "compile_css" as compile_css #lavender
rectangle "copy_simple_asset" as copy_simple_asset #lavender
rectangle "build_site" as build_site #red

' Dependencies from create_directory
create_dir --> geo2gpx
create_dir --> qstarz2gpx
create_dir --> convert_raw
create_dir --> convert_image
create_dir --> convert_audio
create_dir --> text2markdown
create_dir --> markdown2markdown
create_dir --> transcribe_audio
create_dir --> generate_mkdocs_config
create_dir --> build_static_pages
create_dir --> build_day_page
create_dir --> build_gallery
create_dir --> build_journal
create_dir --> build_tags
create_dir --> build_site

' Dependencies for pre_gpx
geo2gpx --> pre_gpx
qstarz2gpx --> pre_gpx

' Dependencies for gpx2gpx
pre_gpx --> gpx2gpx
geo_correlation --> gpx2gpx

' Dependencies from gpx2gpx (using @create_after decorator)
gpx2gpx --> get_gpx_deps
gpx2gpx --> build_day_page
gpx2gpx --> build_gallery
gpx2gpx --> build_journal
gpx2gpx --> build_tags

' Dependencies for build_tags
transcribe_audio --> build_tags

' Dependencies for build_site
build_static_pages --> build_site
generate_mkdocs_config --> build_site
compile_css --> build_site
build_day_page --> build_site
build_gallery --> build_site
build_journal --> build_site
build_tags --> build_site
get_gpx_deps -.-> build_site : calc_dep

' Dependencies for build_static_pages
get_gpx_deps -.-> build_static_pages : calc_dep

' Dependencies for content generation tasks
get_gpx_deps -.-> build_gallery : calc_dep
get_gpx_deps -.-> build_journal : calc_dep
get_gpx_deps -.-> build_tags : calc_dep

' Legend
legend top left
  |Color| Task Type |
  |<#lightblue>| Directory creation |
  |<#lightgreen>| Data conversion |
  |<#yellow>| GPX preprocessing |
  |<#orange>| GPX processing |
  |<#pink>| Audio processing |
  |<#lightcyan>| Content generation |
  |<#lavender>| Site configuration |
  |<#red>| Final build |
  
  Line types:
  — : task_dep (hard dependency)
  - - : calc_dep (calculated dependency)
end legend

@enduml
```

## Task Description

### Directory Creation Tasks
- **create_directory**: Creates all necessary directories for the build process

### Data Conversion Tasks
- **geo2gpx**: Converts GeoJSON/GeoYAML files to GPX format
- **qstarz2gpx**: Converts Qstarz GPS device files to GPX format
- **convert_raw**: Converts CR2 raw image files to JPEG
- **convert_image**: Processes and converts image files
- **convert_audio**: Converts audio files to MP3 format
- **text2markdown**: Converts plain text files to Markdown
- **markdown2markdown**: Processes existing Markdown files

### GPX Processing Tasks
- **pre_gpx**: Preparation step for GPX processing, ensures dependencies are met
- **geo_correlation**: Correlates geographic data with timestamps
- **gpx2gpx**: Main GPX processing task that generates daily GPX files
- **get_gpx_deps**: Calculates dependencies on GPX files for downstream tasks

### Content Generation Tasks
- **transcribe_audio**: Transcribes audio files to text using AI
- **build_day_page**: Generates daily summary pages
- **build_gallery**: Creates photo gallery pages for each day
- **build_journal**: Builds journal entries from various content sources
- **build_tags**: Generates tag-based content organization

### Site Building Tasks
- **generate_mkdocs_config**: Creates the MkDocs configuration file
- **build_static_pages**: Generates static pages like the index
- **compile_css**: Compiles SASS to CSS
- **copy_simple_asset**: Copies static assets (JS, CSS, images)
- **build_site**: Final step that builds the complete MkDocs site

## Dependency Types

The flowchart shows two types of dependencies:
- **Solid arrows** (`task_dep`): Hard dependencies that must complete before the task can start
- **Dotted arrows** (`calc_dep`): Calculated dependencies that are computed at runtime

The `@create_after` decorator is used for tasks that need to be created after other tasks complete, which is represented by the dependencies from `gpx2gpx` to various content generation tasks.