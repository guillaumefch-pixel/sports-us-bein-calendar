test
succeeded now in 11s

1s
Current runner version: '2.336.0'
Runner Image Provisioner
Operating System
Runner Image
GITHUB_TOKEN Permissions
Secret source: Actions
Prepare workflow directory
Prepare all required actions
Getting action download info
Download action repository 'actions/checkout@v6' (SHA:d23441a48e516b6c34aea4fa41551a30e30af803)
Download action repository 'actions/setup-python@v5' (SHA:a26af69be951a213d495a4c3e4e4022e16d87065)
Complete job name: test
0s
Run actions/checkout@v6
Syncing repository: guillaumefch-pixel/sports-us-bein-calendar
Getting Git version info
Temporarily overriding HOME='/home/runner/work/_temp/40514315-601e-4f3c-928e-959932fb7cab' before making global git config changes
Adding repository directory to the temporary git global config as a safe directory
/usr/bin/git config --global --add safe.directory /home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar
Deleting the contents of '/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar'
Determining repository object format
Initializing the repository
Disabling automatic garbage collection
Setting up auth
Fetching the repository
Determining the checkout info
/usr/bin/git sparse-checkout disable
/usr/bin/git config --local --unset-all extensions.worktreeConfig
Checking out the ref
/usr/bin/git log -1 --format=%H
b46e5bea3dc3c7af472f4673df785cb9865defd9
1s
Node 20 is being deprecated. This workflow is running with Node 24 by default. If you need to temporarily use Node 20, you can set the ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true environment variable. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
Run actions/setup-python@v5
Installed versions
4s
Run pip install requests beautifulsoup4
Collecting requests
  Downloading requests-2.34.2-py3-none-any.whl.metadata (4.8 kB)
Collecting beautifulsoup4
  Downloading beautifulsoup4-4.15.0-py3-none-any.whl.metadata (3.8 kB)
Collecting charset_normalizer<4,>=2 (from requests)
  Downloading charset_normalizer-3.5.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (45 kB)
Collecting idna<4,>=2.5 (from requests)
  Downloading idna-3.18-py3-none-any.whl.metadata (6.1 kB)
Collecting urllib3<3,>=1.26 (from requests)
  Downloading urllib3-2.7.0-py3-none-any.whl.metadata (6.9 kB)
Collecting certifi>=2023.5.7 (from requests)
  Downloading certifi-2026.7.22-py3-none-any.whl.metadata (2.5 kB)
Collecting soupsieve>=1.6.1 (from beautifulsoup4)
  Downloading soupsieve-2.9.2-py3-none-any.whl.metadata (4.6 kB)
Collecting typing-extensions>=4.0.0 (from beautifulsoup4)
  Downloading typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Downloading requests-2.34.2-py3-none-any.whl (73 kB)
Downloading charset_normalizer-3.5.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (250 kB)
Downloading idna-3.18-py3-none-any.whl (65 kB)
Downloading urllib3-2.7.0-py3-none-any.whl (131 kB)
Downloading beautifulsoup4-4.15.0-py3-none-any.whl (109 kB)
Downloading certifi-2026.7.22-py3-none-any.whl (136 kB)
Downloading soupsieve-2.9.2-py3-none-any.whl (37 kB)
Downloading typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Installing collected packages: urllib3, typing-extensions, soupsieve, idna, charset_normalizer, certifi, requests, beautifulsoup4

Successfully installed beautifulsoup4-4.15.0 certifi-2026.7.22 charset_normalizer-3.5.1 idna-3.18 requests-2.34.2 soupsieve-2.9.2 typing-extensions-4.16.0 urllib3-2.7.0
1s
Run python f1.py
🔎 EXTRACTION DES DIFFUSIONS F1
================================================================================
Nombre de blocs trouvés : 1

================================================================================
lundi 17 août 2026 Demain 🏎️ 03h30 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 360 🏎️ 13h24 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 360 🏎️ 20h59 Rediff. 🏎️ Formule 1 · Grand Prix de Hongrie Grand Prix de Hongrie Canal+ Sport 360 🏎️ 22h47 Magazine 🏎️ Formule 1 Le podium Canal+ Sport 360 🏎️ 23h07 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 360 mercredi 19 août 2026 J-3 🏎️ 23h28 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 360 jeudi 20 août 2026 J-4 🏎️ 19h45 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 360 🏎️ 20h17 Magazine 🏎️ Formule 1 Le podium Canal+ Sport 360 🏎️ 20h37 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 360 🏎️ 23h46 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 360 vendredi 21 août 2026 J-5 🏎️ 07h45 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 360 🏎️ 08h16 Magazine 🏎️ Formule 1 Le podium Canal+ Sport 360 🏎️ 08h36 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 360 🏎️ 11h02 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 11h14 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 🏎️ 11h46 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 🏎️ 12h08 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 12h15 Direct 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 16h10 Direct 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 17h35 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 17h43 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 🏎️ 18h15 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 🏎️ 23h04 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 360 samedi 22 août 2026 J-6 🏎️ 08h00 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 360 🏎️ 09h25 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 360 🏎️ 10h13 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 11h40 Direct 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 12h56 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 13h20 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 13h31 Magazine 🏎️ Formule 1 On Board F1 Canal+ Sport 🏎️ 14h05 Magazine 🏎️ Formule 1 Formula One, le mag Canal+ Sport 🏎️ 15h15 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 15h27 Magazine 🏎️ Formule 1 Fractionné F1 Canal+ Sport 🏎️ 15h40 Direct 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 20h08 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas RTS 2 🏎️ 23h02 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 360 dimanche 23 août 2026 J-7 🏎️ 11h21 Rediff. 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Canal+ Sport 🏎️ 12h58 Magazine 🏎️ Formule 1 Parade des pilotes F1 Canal+ 🏎️ 13h31 Magazine 🏎️ Formule 1 On Board F1 15' Canal+ 🏎️ 13h52 Magazine 🏎️ Formule 1 La grille Canal+ 🏎️ 14h29 Direct 🏎️ Formule 1 · Grand Prix des Pays-Bas Grand Prix des Pays-Bas Tipik 🏎️ 15h00 D

0s
Node 20 is being deprecated. This workflow is running with Node 24 by default. If you need to temporarily use Node 20, you can set the ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true environment variable. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
Post job cleanup.
(node:1982) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead.
(Use `node --trace-deprecation ...` to show where the warning was created)
1s
Post job cleanup.
/usr/bin/git version
git version 2.54.0
Temporarily overriding HOME='/home/runner/work/_temp/c2f17aa2-fc4a-4f9f-9658-fa85c9bc7d0d' before making global git config changes
Adding repository directory to the temporary git global config as a safe directory
/usr/bin/git config --global --add safe.directory /home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar
Removing SSH command configuration
/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
Removing HTTP extra header
/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
Removing includeIf entries pointing to credentials config files
/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git.path
includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git/worktrees/*.path
includeif.gitdir:/github/workspace/.git.path
includeif.gitdir:/github/workspace/.git/worktrees/*.path
/usr/bin/git config --local --get-all includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git.path
/home/runner/work/_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --unset includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git.path /home/runner/work/_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --get-all includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git/worktrees/*.path
/home/runner/work/_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --unset includeif.gitdir:/home/runner/work/sports-us-bein-calendar/sports-us-bein-calendar/.git/worktrees/*.path /home/runner/work/_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --get-all includeif.gitdir:/github/workspace/.git.path
/github/runner_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --unset includeif.gitdir:/github/workspace/.git.path /github/runner_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --get-all includeif.gitdir:/github/workspace/.git/worktrees/*.path
/github/runner_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git config --local --unset includeif.gitdir:/github/workspace/.git/worktrees/*.path /github/runner_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config
/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
Removing credentials config '/home/runner/work/_temp/git-credentials-0268d999-e450-4ec8-920f-5318fa0a0fcb.config'
0s
Cleaning up orphan processes
Warning: Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/setup-python@v5. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/
