with import <nixpkgs> {};
stdenv.mkDerivation {
  name = "nvim-config";
  # If you need libraries, list them here
  buildInputs = [ libgcc ];
}
