{
  description = "Nix delivery for the professor-contact Codex skill (aarch64-darwin)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/6510408d147d8c5e6d76043e899e9251756f6a75";

    agent-env-nix = {
      url = "github:RekiDunois/agent-env-nix/main";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Source-only for the fixed Python: pdfx.nix is imported with this flake's
    # pkgs/mkAgentPackage, and the same source also exports the pdfx-agent
    # package used as the Stage-2 OCR-mechanism dependency.
    pdf-processing-core = {
      url = "github:ScholarWorkflow/pdf-processing-core/2be1bf850f29b7ccf7bd1b066ae7292aac33fc87";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
    };

    base-skills = {
      url = "github:ScholarWorkflow/base-skills/3ab2ac188e625b8a8ae37b5fa318c579787c3d1e";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
    };

    # paper-analysis follows this repository's base-skills and shared installer,
    # so the installed vision-tools payload is one single evaluation object for
    # both contact and paper-analysis.  Its own pdf-processing-core input stays
    # as declared (an independent library-only source pin).
    paper-analysis = {
      url = "github:ScholarWorkflow/paper-analysis/master";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
      inputs.base-skills.follows = "base-skills";
    };

    # zotero-tools keeps its own pinned build environment on purpose (the same
    # choice professor-research makes for its leaf packages); overriding it here
    # would evaluate a second zotero-tools payload under the same package id.
    zotero-tools.url = "github:ScholarWorkflow/zotero-tools/24eb6cf596c082ac005ccdd800b962fbb6a8e2c8";

    knowledge-tools = {
      url = "github:ScholarWorkflow/knowledge-tools/bdb0db128b7cfccc6a3b20a8d0acee8695d0e211";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
    };

    # professor-collector ships from professor-research's own flake output and
    # keeps that producer's real dependency instance: its browser-pdf-tools
    # input supplies the base/source skill packages, and zotero-tools keeps its
    # owner lock.  Only the two inputs this repository already pins are aligned.
    professor-research = {
      url = "github:ScholarWorkflow/professor-research/bb27533540715c44039c108302f11d3e00d6b62e";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
    };
  };

  outputs = { self, nixpkgs, agent-env-nix, pdf-processing-core, base-skills, paper-analysis, zotero-tools, knowledge-tools, professor-research }:
    let
      system = "aarch64-darwin";
      pkgs = nixpkgs.legacyPackages.${system};
      mkAgentPackage = agent-env-nix.lib.mkAgentPackage;
      mkProject = agent-env-nix.lib.mkProject;

      pdfx = import "${pdf-processing-core}/nix/pdfx.nix" {
        inherit pkgs mkAgentPackage;
      };

      knowledgePackages = knowledge-tools.lib.mkKnowledgePackages {
        inherit pkgs;
        enableHarnesses = [ "codex" ];
      };

      products = import ./nix/contact.nix {
        inherit pkgs mkAgentPackage mkProject pdfx;
        pdfxAgent = pdf-processing-core.packages.${system}.pdfx-agent;
        paperAnalysis = paper-analysis.packages.${system}.paper-analysis;
        zoteroTools = zotero-tools.packages.${system}.zotero-tools;
        humanizerJa = base-skills.packages.${system}.humanizer-ja;
        visionTools = base-skills.packages.${system}.vision-tools;
        extractionToKnowledge = knowledgePackages.extraction-to-knowledge;
        professorCollector = professor-research.packages.${system}.professor-collector;
      };
    in
    {
      packages.${system} = {
        professor-contact-runtime = products.runtime;
        professor-contact = products.package;
        professor-contact-environment = products.project;
        professor-contact-activate = agent-env-nix.lib.mkCachedActivation {
          inherit pkgs;
          environment = products.project;
          name = "professor-contact-activate";
        };
      };
    };
}
