{
  description = "ytalbum — download albums from YouTube by name (yt-dlp powered)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
      in
      {
        packages.default = python.pkgs.buildPythonApplication {
          pname = "ytalbum";
          version = "0.1.0";
          src = ./.;
          pyproject = true;
          build-system = [ python.pkgs.setuptools ];
          dependencies = [ ];

          # ytalbum shells out to these binaries via PATH lookup,
          # so they must be on PATH next to the wrapped entry point.
          makeWrapperArgs = [
            "--prefix" "PATH" ":" (pkgs.lib.makeBinPath [ pkgs.yt-dlp pkgs.ffmpeg ])
          ];

          doCheck = true;
          checkPhase = ''
            runHook preCheck
            ${python.interpreter} -m unittest test_ytalbum -v
            runHook postCheck
          '';

          meta = with pkgs.lib; {
            description = "Download albums from YouTube by name using yt-dlp";
            homepage = "https://github.com/Narla7/youtube-album-downloader";
            license = licenses.mit;
            mainProgram = "ytalbum";
          };
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/ytalbum";
        };

        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.yt-dlp
            pkgs.ffmpeg
            pkgs.uv
          ];
          shellHook = ''
            echo "ytalbum dev shell — try: ./ytalbum.py --help"
          '';
        };

        # NOTE: `mkdir` first — plain `cp -r <dir> <newdir>` trips a
        # path-translation quirk in rootless (proot) sandboxes.
        checks.default = pkgs.runCommand "ytalbum-tests" { } ''
          mkdir source
          cp -r ${./.}/. source/
          chmod -R u+w source
          cd source
          ${python.interpreter} -m unittest test_ytalbum
          touch $out
        '';
      });
}
