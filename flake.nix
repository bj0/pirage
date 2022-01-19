{
   description = "flake to run pirage";

   inputs = {
    flake-utils.url = "github:numtide/flake-utils";
   };

   outputs = { self, nixpkgs, flake-utils }@inp:
    flake-utils.lib.eachDefaultSystem (system:
        let
            pkgs = import inp.nixpkgs { inherit system; };
        in rec {
            packages = flake-utils.lib.flattenTree {
                pirage = pkgs.poetry2nix.mkPoetryApplication {
                    projectDir = ./.;
                };
            };
            defaultPackage = packages.pirage;

            devShell = pkgs.mkShell {
                    buildInputs = [ packages.pirage ];
            };
        }
    );
}