/**
 * Shared Test Helper Functions
 *
 * Common utilities for source code analysis used across all test files.
 * Functions are declared inline to avoid multiple definition errors
 * when linking multiple test files together.
 */

#ifndef TEST_HELPERS_H
#define TEST_HELPERS_H

#include <string>
#include <fstream>
#include <sstream>
#include <regex>

// ============================================================================
// HELPER FUNCTIONS FOR SOURCE CODE ANALYSIS
// ============================================================================

/**
 * Read source file contents into a string
 */
inline std::string read_source_file(const char* filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        return "";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

/**
 * Check if source contains a literal pattern
 */
inline bool source_contains(const std::string& source, const std::string& pattern) {
    return source.find(pattern) != std::string::npos;
}

/**
 * Check if source matches a regex pattern
 */
inline bool source_matches_regex(const std::string& source, const std::string& pattern_str) {
    try {
        std::regex pattern(pattern_str);
        return std::regex_search(source, pattern);
    } catch (...) {
        return false;
    }
}

/**
 * Count occurrences of a pattern in source
 */
inline int count_pattern_occurrences(const std::string& source, const std::string& pattern) {
    int count = 0;
    size_t pos = 0;
    while ((pos = source.find(pattern, pos)) != std::string::npos) {
        count++;
        pos += pattern.length();
    }
    return count;
}

/**
 * Check if pattern exists in source and is NOT commented out
 */
inline bool pattern_active(const std::string& source, const std::string& pattern) {
    size_t pos = source.find(pattern);
    if (pos == std::string::npos) {
        return false;
    }

    // Check if this occurrence is on a commented line
    size_t line_start = source.rfind('\n', pos);
    if (line_start == std::string::npos) {
        line_start = 0;
    } else {
        line_start++;
    }

    std::string line = source.substr(line_start, pos - line_start);
    // If line contains "//" before pattern, it's commented
    return line.find("//") == std::string::npos;
}

/**
 * Extract struct definition from source code
 * Handles nested braces by counting brace depth
 */
inline std::string extract_struct_definition(const std::string& source, const std::string& struct_name) {
    std::string pattern_str = "struct\\s+" + struct_name + "\\s*\\{";
    std::regex pattern(pattern_str);
    std::smatch match;

    if (!std::regex_search(source, match, pattern)) {
        return "";
    }

    // Find matching closing brace
    size_t start = match.position() + match.length();
    int brace_count = 1;
    size_t pos = start;

    while (pos < source.length() && brace_count > 0) {
        if (source[pos] == '{') brace_count++;
        if (source[pos] == '}') brace_count--;
        pos++;
    }

    if (brace_count == 0) {
        return source.substr(match.position(), pos - match.position());
    }

    return "";
}

/**
 * Extract function body from source code
 */
inline std::string extract_function_body(const std::string& source, const std::string& function_name) {
    // Find function definition
    std::string pattern_str = "void\\s+" + function_name + "\\s*\\([^)]*\\)\\s*\\{";
    std::regex pattern(pattern_str);
    std::smatch match;

    if (!std::regex_search(source, match, pattern)) {
        return "";
    }

    // Find matching closing brace
    size_t start = match.position() + match.length();
    int brace_count = 1;
    size_t pos = start;

    while (pos < source.length() && brace_count > 0) {
        if (source[pos] == '{') brace_count++;
        if (source[pos] == '}') brace_count--;
        pos++;
    }

    if (brace_count == 0) {
        return source.substr(match.position(), pos - match.position());
    }

    return "";
}

/**
 * Count field declarations in a struct definition
 * Counts semicolons which mark the end of each field
 */
inline int count_struct_fields(const std::string& struct_def) {
    int field_count = 0;
    for (char c : struct_def) {
        if (c == ';') {
            field_count++;
        }
    }
    return field_count;
}

#endif // TEST_HELPERS_H
