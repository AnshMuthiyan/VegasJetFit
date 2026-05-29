# Documentation for VegasAfterglow

This directory contains the documentation for the VegasAfterglow project.

## Building the Documentation

### Prerequisites

- Python 3.9 or later
- Doxygen (for C++ API documentation)
- Graphviz (for diagrams)
- Sphinx and related packages

### Install Dependencies

```bash
pip install sphinx sphinx-rtd-theme breathe
```

### Build Process

You can build the documentation using the provided script:

```bash
cd docs
chmod +x build_docs.sh
./build_docs.sh
```

The built documentation will be in the `build/html` directory.

## Documentation Structure

- `source/` - Contains the RST files for Sphinx
- `doxygen/` - Output directory for Doxygen (generated)
- `build/` - Output directory for Sphinx (generated)
- `Doxyfile` - Configuration for Doxygen
- `source/conf.py` - Configuration for Sphinx

## Automatic Deployment

The documentation is automatically built and deployed to the GitHub Wiki whenever changes are pushed to the `main` branch and affect files in the `docs/`, `include/`, `src/`, or `pybind/` directories.

### Manual Deployment

To manually trigger the documentation build and deployment, you can run:

```bash
gh workflow run docs.yml
```

## Documentation Guidelines

### C++ Documentation

Use Doxygen-style comments for C++ code:

```cpp
/**
 * @brief Brief description of the function/class
 * @details Detailed description
 *
 * @param param1 Description of first parameter
 * @param param2 Description of second parameter
 * @return Description of return value
 */
```

For proper display of comments in documentation, make sure to:

1. Use `///` or `/**` style comments for documentation that should appear in the docs
2. Place your documentation comments immediately before the item they document
3. Document all parameters, return values, and exceptions
4. Use appropriate Doxygen commands (`@brief`, `@details`, `@param`, etc.)

#### Documenting Implementation Files

Comments in .cpp implementation files are now fully included in the documentation. To ensure implementation details are properly documented:

1. Use the same Doxygen comment style in both header and implementation files
2. For implementation-specific details, add comments directly inside the implementation:

```cpp
void MyClass::complexMethod(int param1, double param2) {
    // Implementation comments will be included in the documentation

    /*
     * Longer implementation comments will also be visible
     * in the documentation.
     */

    // Step 1: Initialize calculation
    double result = 0.0;

    // Step 2: Complex algorithm explanation here
    for (int i = 0; i < param1; i++) {
        // This algorithm uses the following approach...
        result += std::sin(i * param2);
    }

    return result;
}
```

3. For functions with different implementations based on configuration, document the implementation details:

```cpp
#ifdef USE_OPTIMIZED_VERSION
// This optimized implementation uses SIMD instructions for parallel computation
void calculateValues(std::vector<double>& values) {
    // Implementation details...
}
#else
// This standard implementation is more portable but slower
void calculateValues(std::vector<double>& values) {
    // Implementation details...
}
#endif
```

4. You can view implementation details in the documentation by clicking the "Browse Source Code Implementation" link on the main documentation page.

Example for comprehensive class documentation:

```cpp
/**
 * @class MyClass
 * @brief Brief description of the class
 * @details Detailed description of the class and its purpose
 *
 * This class provides functionality for...
 * Usage example:
 * @code
 * MyClass obj;
 * obj.doSomething();
 * @endcode
 */
class MyClass {
public:
    /**
     * @brief Constructor for MyClass
     * @param param1 Description of parameter
     */
    MyClass(int param1);

    /**
     * @brief Method description
     * @param param Description of parameter
     * @return Description of return value
     * @throw std::exception If something goes wrong
     */
    int doSomething(double param);

private:
    int m_member; ///< Description of member variable
};
```

### Python Documentation

Use Google-style docstrings for Python code:

```python
def function(param1, param2):
    """Brief description of the function.

    Detailed description of the function.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Description of return value
    """
```

### Template and Inline Functions

For template and inline functions, ensure you document both template parameters and function parameters:

```cpp
/**
 * @brief Brief description of the template function
 * @details Detailed description
 *
 * @tparam T Description of template parameter
 * @param param1 Description of first parameter
 * @return Description of return value
 */
template<typename T>
inline T function(T param1) { return param1; }
```

## Comment Display Configuration

Our documentation system has been configured to:

1. Show all comments in the source code, including private members and implementation details
2. Display inherited members with their comments
3. Include full documentation for template classes and functions
4. Highlight and properly format comments in the generated HTML
5. Show inline documentation in class definitions
6. Provide direct access to the implementation source code with comments

## Troubleshooting Comment Display

If your comments are not appearing in the documentation:

1. Check that you're using proper Doxygen syntax (`///` or `/**` style)
2. Ensure the comment is placed directly before the item it documents
3. Make sure the file is included in the documentation input paths in `Doxyfile`
4. Verify that the comment is not excluded by any pattern in `EXCLUDE_PATTERNS` or `EXCLUDE_SYMBOLS`
5. For implementation files, ensure they're in the correct directory (../src) and have matching header files

For specific formatting issues:

1. Use Markdown in your comments for better formatting
2. Use `@code`/`@endcode` for code examples
3. Use `@note`, `@warning`, etc. for special callouts

## Source Code Browser

The documentation now includes a source code browser that shows the full implementation files with comments. You can access it by:

1. Opening the main documentation page
2. Clicking the "Browse Source Code Implementation" link at the bottom of the page
3. Navigating to the specific source file you want to examine

This is particularly useful for viewing implementation-specific comments that describe algorithm details, optimization techniques, and internal workings of the code.

## Customizing Documentation

- Edit `source/conf.py` to modify Sphinx configuration
- Edit `Doxyfile` to modify Doxygen configuration
