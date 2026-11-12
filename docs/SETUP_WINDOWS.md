# Windows setup

Use WSL2 with Ubuntu and keep the checkout in the WSL filesystem.

```sh
sudo apt update
sudo apt install -y git git-lfs python3 python3-venv python3-pip
git lfs install
git clone https://github.com/valentinopapangeok/IRIDE.git ~/IRIDE
cd ~/IRIDE
./products/clone-products.sh
```

Create component-specific virtual environments rather than one global environment.
For local input-availability runs, restore the private file as:

```text
apps/input-availability/input_availability/config.json
```

That path is ignored by Git. Never commit credentials.
