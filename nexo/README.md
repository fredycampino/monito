# Nexo

Independent host development agent for Monito, Ggets and deployments. Monito Box
has no dependency on this directory. The legacy monito/ development agent has
been removed; use Nexo for new development tasks. Historical run records remain
unchanged, but old development sessions should not be resumed.

From the repository root, start a new session with:

`skiller ./nexo/nexo.yaml`

The explicit agent.dev.json profile preserves the development permissions and
uses the existing global LLM/provider settings. No credentials or run databases
are copied. This creates a new run; it does not rename or migrate an active run.
No global flow registration is changed, so use the YAML path rather than
assuming @nexo is configured.

contexto/page-oct-20.md is historical continuity, loaded on demand. The active
prompt uses system.md and the local instructions in instructions/ plus standard
Skiller instructions, with no dependency on the old monito/ directory.
