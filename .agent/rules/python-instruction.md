---
trigger: always_on
---

1. In a python codebase, after each edit session, run Ruff to check and then lint the modified files and codes. To do it, use the terminal command `uvx ruff check` and `uvx ruff format`. If there is any lint errors not fixed by the `format` command, please analyze what might be the cause of the errors. Then, check how much change is needed to fix the errors. If it only requires light editing that will not change any working part of the code, please fix it. Otherwise, please refrain from editing, and just provide an explanation and suggested fixes.
2. Python codes should be strongly typed. To help with that, use the pyrefly toolings. To check if there is any typing errors, please use the `uvx pyrefly check /path/to/file.py --summarize-errors` command. Makesure beforehand that you are in the current project directory. Please avoid global typecheck, only do file check instead. To automatically infer types using pyrefly, use the `pyrefly infer path/to/directory/` command for directories and `pyrefly infer path/to/file.py` for specific files.Here is the full list of commands for the pyrefly:

```
Commands:
  check        Full type checking on a file or a project
  snippet      Check a Python code snippet
  dump-config  Dump info about pyrefly's configuration. Use by replacing `check` with `dump-config` in your pyrefly invocation   
  buck-check   Entry point for Buck integration
  init         Initialize a new pyrefly config in the given directory, or migrate an existing mypy or pyright config to pyrefly  
  lsp          Start an LSP server
  tsp          Start a TSP server
  infer        Automatically add type annotations to a file or directory
  report       Generate reports from pyrefly type checking results
  help         Print this message or the help of the given subcommand(s)

Options:
  -j, --threads <THREADS>  Number of threads to use for parallelization. Setting the value to 1 implies sequential execution     
                           without any parallelism. Setting the value to 0 means to pick the number of threads automatically     
                           using default heuristics [env: PYREFLY_THREADS=] [default: 0]
      --color <COLOR>      Control whether colored output is used [env: PYREFLY_COLOR=] [default: auto] [possible values: auto,  
                           always, never]
  -v, --verbose            Enable verbose logging [env: PYREFLY_VERBOSE=]
  -h, --help               Print help
  -V, --version            Print version
```


3. Use the `filesystem` and 'octocode' mcp tools to perform codebase analysis before you decide on how to implement things. Use all available tools thoroughout your editing process, including but not limited to search, code editing, filesystem operations, among many others. 
4. Always use the context7 mcp tools to get relevant documentations regarding the implementation that is asked of you.
6. In python projects, prefer object oriented programming where functions are organized as classes.
7. Always add easy to understand but detailed docstrings to function, classes and other important part of a file/scripts. Assume that the reader of the docstrings do not have specialized expertise on the function/part of the code, but, still have a basic understanding of pythons and commonly used libraries.
8. Always make sure that you are running terminal commands using the project's virtual environment setup by uv project manager. To activate the virtual environment, use the command `.venv/Scripts/activate` on Windows.
9. As the codebases is using uv package manager, please use the available uv commands. Here's the list of the uv commands:

```
Commands:
  run                        Run a command or script
  init                       Create a new project
  add                        Add dependencies to the project
  remove                     Remove dependencies from the project
  sync                       Update the project's environment
  lock                       Update the project's lockfile
  export                     Export the project's lockfile to an alternate format
  tree                       Display the project's dependency tree
  tool                       Run and install commands provided by Python packages
  python                     Manage Python versions and installations
  pip                        Manage Python packages with a pip-compatible interface
  venv                       Create a virtual environment
  build                      Build Python packages into source distributions and wheels
  publish                    Upload distributions to an index
  cache                      Manage uv's cache
  self                       Manage the uv executable
  version                    Display uv's version
  generate-shell-completion  Generate shell completion
  help                       Display documentation for a command
```

10. Please refer to the `machine_specifications.md` at the root dictionary of the project when you are about to make an edit or decisions where the OS and the hardware specifications such as the size of the RAM is important.
11. As the main operating system where the project is developed on, and powershell is the default shell, please write your terminal command accordingly. Avoid using the '&&' to run multiple lines of commmands when you use terminal.