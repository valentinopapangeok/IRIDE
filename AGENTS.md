# IRIDE monorepo

This repository contains operational applications, evidence, validation code and
shared tools. Read the nearest nested `AGENTS.md` before changing a component.

- Do not commit credentials, provider downloads, validation caches, databases,
  virtual environments or workstation-specific configuration.
- Preserve operational evidence and workbook provenance.
- Keep product repositories independently versioned and deployed.
- Input-availability automation must keep local config and GitHub Actions secret
  behaviour aligned.
- Run tests from the component directory and scope changes to the affected area.
