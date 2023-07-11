export dry=True
export GREEN=$(tput setaf 2 :-"" 2>/dev/null)
export RESET=$(tput sgr0 :-"" 2>/dev/null)

if [ ! -d "./venv" ]; then
    bash ./install.sh
    echo $GREEN; printf -- "-%.0s" $(seq $(tput cols)); echo $RESET
    echo $GREEN;echo "Running script"; echo $RESET
fi

while [ $# -gt 0 ]; do
    if [[ $1 == "--"* ]]; then
        v="${1/--/}"
        declare "$v"="$2"
        shift
    fi
    shift
done

if [ $dry == "True" ]; then
    python3 main.py --dry-run $([ -n "$issues" ] && echo "--issues=$issues") $([ -n "$start" ] && echo "--start=$start") $([ -n "$end" ] && echo "--end=$end") $([ -n "$fetchRelease" ] && echo "--fetchRelease=$fetchRelease")
else
    python3 main.py $([ -n "$issues" ] && echo "--issues=$issues") $([ -n "$start" ] && echo "--start=$start") $([ -n "$end" ] && echo "--end=$end") $([ -n "$fetchRelease" ] && echo "--fetchRelease=$fetchRelease")
fi
