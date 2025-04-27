#!/bin/bash

# eslint-filter.sh
# A helper script to run eslint and filter output by specific rule types

# Setup proper error handling and cleanup
set -e # Exit immediately if a command exits with a non-zero status

# Initialize temp_dir variable
temp_dir=""

# Cleanup function to ensure temporary files are always removed
cleanup() {
  if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
    rm -rf "$temp_dir"
    [ "$verbose" = true ] && echo "Cleaned up temporary files" >&2
  fi
}

# Set up trap to call cleanup function on script exit, interrupt, or error
trap cleanup EXIT INT TERM

# Initialize variables
rules=()
verbose=false
help=false
group_by_rule=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --rule)
      if [[ -n $2 ]]; then
        rules+=("$2")
        shift 2
      else
        echo "Error: --rule requires a value"
        exit 1
      fi
      ;;
    --group-by-rule)
      group_by_rule=true
      shift
      ;;
    --verbose|-v)
      verbose=true
      shift
      ;;
    --help|-h)
      help=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      help=true
      shift
      ;;
  esac
done

# Show help if requested or no rules provided
if [[ "$help" = true || ${#rules[@]} -eq 0 ]]; then
  echo "Usage: $(basename "$0") [OPTIONS]"
  echo ""
  echo "OPTIONS:"
  echo "  --rule RULE_NAME     Filter eslint output by this rule (can be used multiple times)"
  echo "  --group-by-rule      Group output by rule rather than by file (default: group by file)"
  echo "  --verbose, -v        Show full eslint output before filtering"
  echo "  --help, -h           Show this help message"
  echo ""
  echo "Example: $(basename "$0") --rule vue/no-lone-template --rule vue/order-in-components"
  echo "Example: $(basename "$0") --rule vue/no-lone-template --group-by-rule"
  exit 0
fi

# Function to convert a rule name to a safe filename
safe_filename() {
  echo "$1" | tr '/' '_'
}

# Run eslint and capture output in a variable
echo "Running eslint..."
eslint_output=$(npm run lint 2>&1) || { echo "ESLint command failed"; exit 1; }

# Display full output if verbose mode is enabled
if [[ "$verbose" = true ]]; then
  echo "Full eslint output:"
  echo "$eslint_output"
  echo ""
  echo "Filtered results:"
fi

if [[ "$group_by_rule" = true ]]; then
  # Process eslint output grouped by rule using temporary files
  # Create a temporary directory with appropriate permissions
  temp_dir=$(mktemp -d) || { echo "Failed to create temporary directory"; exit 1; }

  # Process the eslint output to collect warnings by file first
  current_file=""

  # First pass: Save the complete output to a temporary file
  echo "$eslint_output" > "$temp_dir/full_output.txt"

  # Find all unique rules in the output
  for rule in "${rules[@]}"; do
    # Create safe filename for this rule
    safe_rule=$(safe_filename "$rule")

    # Extract warnings for this rule and save to a separate file
    echo "$rule" > "$temp_dir/${safe_rule}.rule"

    # Create file to store all files affected by this rule
    touch "$temp_dir/${safe_rule}.files"

    # Process the full output line by line to extract warnings for this rule
    current_file=""
    warning_line=""

          while IFS= read -r line; do
      # Check if line is a file path
      if [[ "$line" == /* && ("$line" == *".vue" || "$line" == *".js") ]]; then
        current_file="$line"
      elif [[ ! -z "$current_file" && "$line" =~ [0-9]+:[0-9]+ ]] && [[ "$line" == *"$rule"* ]]; then
        # This is a warning line for the current rule
        # Save file and warning together
        echo -e "\n$current_file" >> "$temp_dir/${safe_rule}.pairs"
        echo "  $line" >> "$temp_dir/${safe_rule}.pairs"

        # Also save the file path to the list of affected files
        echo "$current_file" >> "$temp_dir/${safe_rule}.files"
      fi
    done < "$temp_dir/full_output.txt"
  done

  # Output the grouped results
  for rule in "${rules[@]}"; do
    # Create safe filename for this rule
    safe_rule=$(safe_filename "$rule")

    if [[ -f "$temp_dir/${safe_rule}.rule" ]]; then
      # Output the rule
      cat "$temp_dir/${safe_rule}.rule"

      # Output file/warning pairs if they exist
      if [[ -f "$temp_dir/${safe_rule}.pairs" ]]; then
        cat "$temp_dir/${safe_rule}.pairs"
      fi
      echo ""
    fi
  done

  # Cleanup happens automatically via the trap
else
  # Process eslint output line by line (grouped by file, original version)
  current_file=""
  file_has_matching_rules=false

  # Function to check if a line contains any of the specified rules
  contains_rule() {
    local line=$1
    for rule in "${rules[@]}"; do
      if [[ "$line" == *"$rule"* ]]; then
        return 0
      fi
    done
    return 1
  }

  # First pass: Find files with matching rules and store their warnings
  temp_dir=$(mktemp -d) || { echo "Failed to create temporary directory"; exit 1; }
  touch "$temp_dir/file_warnings.txt"

  while IFS= read -r line; do
    # Check if line is a file path
    if [[ "$line" == /* && ("$line" == *".vue" || "$line" == *".js") ]]; then
      # If we were processing a file and found matching rules, write a blank line after it
      if [[ "$file_has_matching_rules" = true ]]; then
        echo "" >> "$temp_dir/file_warnings.txt"
      fi

      current_file="$line"
      file_has_matching_rules=false
    # Check if line contains any of the specified rules
    elif contains_rule "$line"; then
      if [[ "$file_has_matching_rules" = false ]]; then
        echo -e "\n$current_file" >> "$temp_dir/file_warnings.txt"
        file_has_matching_rules=true
      fi
      echo "  $line" >> "$temp_dir/file_warnings.txt"
    fi
  done < <(echo "$eslint_output")

  # Output the filtered warnings
  if [[ -s "$temp_dir/file_warnings.txt" ]]; then
    cat "$temp_dir/file_warnings.txt"
  else
    echo "No matching warnings found for the specified rules."
  fi
fi

# Note: cleanup function will automatically run thanks to the trap