# Bash completion script for songml-* commands
#
# Installation:
#   songml-bashcompletion > ~/.config/bash_completion.d/songml
#   source ~/.config/bash_completion.d/songml
#

# Simple initialization for our completion functions
_songml_init() {
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD
}

_songml_create() {
    local cur prev words cword
    _songml_init

    case "$prev" in
        -h|--help)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "-h --help" -- "$cur") )
        return 0
    fi

    # No file completion for create
    return 0
}

_songml_format() {
    local cur prev words cword
    _songml_init

    case "$prev" in
        -h|--help)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "-h --help -i --inplace" -- "$cur") )
        return 0
    fi

    # Complete .songml files
    COMPREPLY=( $(compgen -f -X '!*.songml' -- "$cur") )
    if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
        COMPREPLY=( $(compgen -d -- "$cur") )
    fi
    return 0
}

_songml_validate() {
    local cur prev words cword
    _songml_init

    case "$prev" in
        -h|--help)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "-h --help" -- "$cur") )
        return 0
    fi

    # Complete .songml files
    COMPREPLY=( $(compgen -f -X '!*.songml' -- "$cur") )
    if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
        COMPREPLY=( $(compgen -d -- "$cur") )
    fi
    return 0
}

_songml_to_midi() {
    local cur prev words cword
    _songml_init

    case "$prev" in
        -h|--help)
            return 0
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "-h --help" -- "$cur") )
        return 0
    fi

    # Complete .songml files for input, .mid files for output
    local arg_count=0
    for ((i=1; i<cword; i++)); do
        if [[ "${words[i]}" != -* ]]; then
            ((arg_count++))
        fi
    done

    if [[ $arg_count -eq 0 ]]; then
        # First arg: .songml files
        COMPREPLY=( $(compgen -f -X '!*.songml' -- "$cur") )
        if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
            COMPREPLY=( $(compgen -d -- "$cur") )
        fi
    elif [[ $arg_count -eq 1 ]]; then
        # Second arg: .mid files
        COMPREPLY=( $(compgen -f -X '!*.mid' -- "$cur") )
        if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
            COMPREPLY=( $(compgen -d -- "$cur") )
        fi
    fi
    return 0
}

_songml_bashcompletion() {
    local cur prev words cword
    _songml_init

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "-h --help" -- "$cur") )
        return 0
    fi

    return 0
}

# Register completion functions for both with and without .exe extension
# (needed for Windows/Git Bash where executables have .exe suffix)
complete -F _songml_create songml-create
complete -F _songml_create songml-create.exe
complete -F _songml_format songml-format
complete -F _songml_format songml-format.exe
complete -F _songml_validate songml-validate
complete -F _songml_validate songml-validate.exe
complete -F _songml_to_midi songml-to-midi
complete -F _songml_to_midi songml-to-midi.exe
complete -F _songml_bashcompletion songml-bashcompletion
complete -F _songml_bashcompletion songml-bashcompletion.exe

# vim: ft=bash
