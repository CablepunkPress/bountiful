# Bountiful

Local Agent Application

Bountiful is built on [llama.cpp](https://github.com/ggml-org/llama.cpp), an open-source program that runs AI models on local hardware. The build compiles it from source for your machine.

## Hardware

Bountiful is tested on and optimized for the following:

- Apple M6 Mac Mini 32 GB
- Nvidia GeForce RTX 3060 12 GB with 32 GB DDR4 system memory on GNU/Linux

## Prepare your Mac

Bountiful needs Homebrew, a current version of Python, and cmake, a tool for building software from source.

Homebrew's installer also sets up Apple's Command Line Tools, which provide git and a compiler. Open Terminal on your Mac and run the following command from Homebrew's [website](https://brew.sh/):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

When the installer finishes, it prints a few "Next steps" commands. Run them to make the `brew` command available in your terminal.

Then install Python and cmake, and check the Python version:

```bash
brew install python cmake
python3 --version
```

It should report Python 3.14 or newer.

## Prepare your GNU/Linux machine

For GNU/Linux machines, Bountiful builds llama.cpp with Vulkan, so it needs Python, git, cmake, a C++ compiler, and the Vulkan development files.

On Arch and CachyOS:

```bash
sudo pacman -S python git cmake gcc vulkan-headers shaderc spirv-headers
```

On Debian and Ubuntu:

```bash
sudo apt install python3 python3-venv git cmake g++ libvulkan-dev glslc spirv-headers
```

To check that your graphics card is ready, run `vulkaninfo --summary` (from the `vulkan-tools` package). Your card should be on the list.

Check your Python version:

```bash
python3 --version
```

It should report Python 3.14 or newer.

## Install Bountiful

Clone Bountiful into your home folder and build it:

```bash
cd ~
git clone https://github.com/CablepunkPress/bountiful.git
cd bountiful
python3 build.py
```

Confirm you wish to install Bountiful and the `bountiful` command. At this point, setup will download llama.cpp and the required AI models, approximately 35 GB.

Once setup is complete, open a new terminal window to create your agent.

## Create your agent

Use the `bountiful` command to create your agent. The example here is for an agent named Alice.

```bash
bountiful create Alice
```

Your agent's ID and home folder are derived from its name. Everything that is unique about your agent, from its editable persona to its memories, lives in its folder, `~/alice` in this example.

## Start your agent

Use the `bountiful` command followed by your agent's ID to start your agent. For example:

```bash
bountiful alice
```

Open `http://localhost:11777` in your favorite web browser to interact with your agent. To end the session, return to the terminal and press Control-C.

## 'bountiful' commands

Run `bountiful` by itself in the terminal to see available commands.

## License

MIT
