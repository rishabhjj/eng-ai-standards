# eng-ai base for Java (reference snippets, not yet validated against a real build)

Gradle (Kotlin DSL) with the `net.ltgt.errorprone` and `com.diffplug.spotless` plugins:

```kotlin
tasks.withType<JavaCompile>().configureEach {
    options.errorprone {
        // ERR-001: empty catch blocks are errors
        error("EmptyCatch")
        // TYP-001: null-safety. NullAway needs the annotatedPackages option
        error("NullAway")
        option("NullAway:AnnotatedPackages", "com.yourcompany")
    }
}

spotless {
    java { googleJavaFormat() }
}
```

- ERR-001: `EmptyCatch`, plus SpotBugs for swallowed exceptions.
- TYP-001: `NullAway` removes unchecked nulls.
- CPX-001: Checkstyle `CyclomaticComplexity` with `max = 10`.
