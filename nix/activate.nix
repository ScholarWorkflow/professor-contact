{ pkgs, environment }:

pkgs.runCommand "professor-contact-activate" { } ''
  mkdir -p "$out/bin"
  substitute ${./activate.sh} "$out/bin/professor-contact-activate" \
    --replace-fail '@bash@' '${pkgs.bash}' \
    --replace-fail '@coreutils@' '${pkgs.coreutils}' \
    --replace-fail '@environment@' '${environment}'
  chmod 0555 "$out/bin/professor-contact-activate"
''
