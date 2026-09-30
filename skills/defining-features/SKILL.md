---
name: defining-features
description: Use when starting a new project or when .specs/memory/features.md is missing or empty.
---

# Skill: defining-features

## Overview
Guides the user to define the list of features for the project.

## Checklist
1. Use the Read tool on `.specs/memory/features.md`. If it has content, exit and do nothing.
2. Use the Read tool on `.specs/templates/features_template.md`. To know what questions to ask to create the features list. 
3. Ask the user to list the features they want to build (e.g., Auth, Database). Follow the structure on `.specs/templates/features_template.md` if it exists
4. Use the Write tool to save the features to `.specs/memory/features.md` in a structured list format.

## Next steps
Once `.specs/memory/features.md` is written, you MUST immediately invoke the brainstorming skill before doing anything else. Use the Skill tool with the name `brainstorming`. Do not write code, scaffold files, or proceed to implementation until brainstorming is complete.