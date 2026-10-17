{ pkgs
, mkAgentPackage
, mkProject
, pdfx
, pdfxAgent
, paperAnalysis
, zoteroTools
, humanizerJa
, visionTools
, extractionToKnowledge
}:

# Nix delivery for the professor-contact Codex skill (aarch64-darwin).
#
# The APM sources under ../.apm/ and ../packages/professor-contact-codex/.apm/
# remain the only business source.  This file adds the bounded install-time
# binding: the seven same-directory entries are installed with the fixed
# interpreter in their shebang, the router entry gets one locked Zotero exporter,
# the handoff entry exports the locked helper interpreter, and the Codex
# Stage-5 routing appendix is added to the generated SKILL.md and coordinator
# instructions.  It never keeps a second copy of the business body and never
# rewrites the source orchestration rules.

let
  inherit (pkgs) lib;

  fail = message: throw "professor-contact-nix: ${message}";

  version = "0.1.0";

  # ------------------------------------------------------------- frontmatter

  # Source role documents carry exactly one "---" frontmatter separator.
  splitFrontmatter = label: file:
    let parts = lib.splitString "\n---\n" (builtins.readFile file);
    in if builtins.length parts == 2
    then {
      frontmatter = builtins.head parts;
      body = builtins.elemAt parts 1;
    }
    else fail "${label} must contain exactly one '---' frontmatter separator";

  # Read one single-line YAML scalar without pretending to be a YAML parser:
  # the role sources use one plain or single-quoted line per key.  A
  # single-quoted scalar may escape a quote as '' (the two affected role
  # descriptions do); anything else that needs escaping is rejected instead of
  # silently mis-parsed.
  frontmatterScalar = label: key: frontmatter:
    let
      prefix = "${key}: ";
      matches = builtins.filter (line: lib.hasPrefix prefix line) (lib.splitString "\n" frontmatter);
    in
    if builtins.length matches != 1
    then fail "${label}: expected exactly one '${key}:' frontmatter line"
    else
      let raw = lib.removePrefix prefix (builtins.head matches);
      in if lib.hasPrefix "'" raw
      then
        if !(lib.hasSuffix "'" raw) || builtins.stringLength raw < 2
        then fail "${label}: '${key}' has an unterminated YAML single-quoted scalar"
        else lib.replaceStrings [ "''" ] [ "'" ] (builtins.substring 1 (builtins.stringLength raw - 2) raw)
      else if lib.hasPrefix "\"" raw
      then fail "${label}: '${key}' uses a double-quoted YAML scalar this bounded conversion does not support"
      else raw;

  lstrip = text:
    let
      head = builtins.substring 0 1 text;
      rest = builtins.substring 1 (builtins.stringLength text - 1) text;
    in if head == "\n" || head == " " || head == "\t" then lstrip rest else text;

  # One role document -> the Codex role fields the shared installer accepts.
  # The declared name must match the exported agent name so a renamed source
  # fails this build instead of publishing an agent under the wrong identity.
  role = label: file:
    let
      parsed = splitFrontmatter label file;
      name = frontmatterScalar label "name" parsed.frontmatter;
    in
    if name != label
    then fail "${label}: frontmatter name is '${name}', expected '${label}'"
    else {
      description = frontmatterScalar label "description" parsed.frontmatter;
      developer_instructions = lstrip parsed.body;
    };

  # ------------------------------------------------------------- appendices

  # The Codex-only Stage-5 routing appendix stays a source file; the installed
  # skill copies it verbatim as a resource and appends the same text to the
  # generated SKILL.md and the coordinator role, so both entry points read it.
  routingAppendixFile = ../packages/professor-contact-codex/.apm/instructions/stage5-routing.instructions.md;
  routingAppendix = builtins.readFile routingAppendixFile;

  skillText = pkgs.writeText "professor-contact-SKILL.md"
    (builtins.readFile ../.apm/skills/professor-contact/SKILL.md + "\n" + routingAppendix);

  coordinator = role "professor-contact" ../.apm/agents/professor-contact.agent.md;

  agents = {
    professor-contact = coordinator // {
      developer_instructions = coordinator.developer_instructions + "\n\n" + routingAppendix;
    };
    professor-contact-downloader = role "professor-contact-downloader" ../.apm/agents/professor-contact-downloader.agent.md;
    professor-contact-idea-generator = role "professor-contact-idea-generator" ../.apm/agents/professor-contact-idea-generator.agent.md;
    professor-contact-selection = role "professor-contact-selection" ../.apm/agents/professor-contact-selection.agent.md;
    professor-contact-email-generator = role "professor-contact-email-generator" ../.apm/agents/professor-contact-email-generator.agent.md;
    professor-contact-email-validator = role "professor-contact-email-validator" ../.apm/agents/professor-contact-email-validator.agent.md;
    professor-contact-style-validator = role "professor-contact-style-validator" ../.apm/agents/professor-contact-style-validator.agent.md;
    # The Stage-2 analyzer ships only from the Codex package projection; the
    # OpenCode analyzer is a different harness contract and is never mixed in.
    professor-contact-analyzer = role "professor-contact-analyzer"
      ../packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md;
  };

  # ----------------------------------------------------------------- runtime

  # Fixed interpreter for the seven same-directory entries.  The pdfx python
  # environment is the same interpreter the installed paper-analysis helpers
  # use, so the handoff helper and its facts sibling stay on one version.
  fixedPython = "${pdfx.python}/bin/python3";

  entryNames = [
    "contact_targets"
    "contact_stage1"
    "contact_state"
    "stage2_chatgpt_handoff"
    "stage2_zotero_rpc"
    "stage2_input_router"
    "stage5_immutable"
  ];

  # The staged skill tree is the runtime output: the complete own resources
  # (scripts, docs, tests, hidden helpers) plus the fixed entry points.  It is
  # an ordinary derivation and does not claim to be the agent install.
  runtime = pkgs.runCommand "professor-contact-runtime" { } ''
    mkdir -p "$out"
    cp -R ${../.apm/skills/professor-contact}/. "$out/"
    chmod -R u+w "$out"

    # The Codex routing appendix is a skill resource as well as generated text.
    cp ${routingAppendixFile} "$out/docs/stage5-routing.instructions.md"
    chmod u+w "$out/docs/stage5-routing.instructions.md"
    cp ${skillText} "$out/SKILL.md"
    chmod u+w "$out/SKILL.md"

    ${lib.concatMapStringsSep "\n" (name: ''
      substituteInPlace "$out/scripts/${name}" \
        --replace-fail '#!/usr/bin/env python3' '#!${fixedPython}'
      chmod 0555 "$out/scripts/${name}"
    '') entryNames}

    # The router entry binds the caller's loaded-skill locator to the exporter
    # shipped with this install; the marker keeps the non-Nix default intact.
    substituteInPlace "$out/scripts/stage2_input_router" \
      --replace-fail 'return ""  # NIX_STAGING_EXPORTER: empty keeps the caller-supplied locator' \
      'return "${zoteroTools}/bin/zotero-item-export"  # NIX_STAGING_EXPORTER: locked zotero-tools exporter'

    # The handoff entry exports the same locked interpreter to the PEP-723
    # paper-analysis helpers, which then skip the uv default backend.
    substituteInPlace "$out/scripts/stage2_chatgpt_handoff" \
      --replace-fail 'return ""  # CONTACT_PAPER_PYTHON: empty keeps the non-Nix uv default' \
      'return "${fixedPython}"  # CONTACT_PAPER_PYTHON: locked pdfx interpreter'

    grep -F '${fixedPython}' "$out/scripts/stage2_input_router" "$out/scripts/stage2_chatgpt_handoff" >/dev/null
    test -x "$out/scripts/stage2_input_router"
  '';

  # --------------------------------------------------------------- packaging

  # Direct dependencies are exactly the delivered producer objects named by the
  # approved plan.  professor-research has not published a Nix package for
  # professor-collector yet (its PR #35 is still a plan), so contact's Stage-1
  # missing-PDF fill and Stage-5 contact-evidence checker edge cannot be pinned
  # here; no revision may be fabricated, and the environment stays the closure
  # of the packages below until that producer output exists.
  agentDependencies = [
    paperAnalysis
    zoteroTools
    humanizerJa
    visionTools
    pdfxAgent
    extractionToKnowledge
  ];

  package = mkAgentPackage {
    inherit pkgs;
    id = "professor-contact";
    inherit version;
    files."skills/professor-contact" = runtime;
    exports = {
      skills.professor-contact = "skills/professor-contact";
      inherit agents;
    };
    inherit agentDependencies;
    runtimePackages = [ pdfx.python ];
    enableHarnesses = [ "codex" ];
  };

  project = mkProject {
    inherit pkgs;
    name = "professor-contact-environment";
    roots = [ package ];
  };
in
{
  inherit runtime package project agents agentDependencies entryNames;
}
