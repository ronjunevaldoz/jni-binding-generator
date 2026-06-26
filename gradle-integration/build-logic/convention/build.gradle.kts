plugins {
    `kotlin-dsl`
    `maven-publish`
}

group = "io.github.ronjunevaldoz"
version = "0.37.0"

publishing {
    publications {
        create<MavenPublication>("pluginMaven") {
            artifactId = "jni-binding-generator-plugin"
            pom {
                name.set("JNI Binding Generator Plugin")
                description.set("Gradle convention plugin that generates C++ JNI stubs from Kotlin external fun declarations.")
                url.set("https://github.com/ronjunevaldoz/jni-binding-generator")
                licenses {
                    license {
                        name.set("Apache-2.0")
                        url.set("https://www.apache.org/licenses/LICENSE-2.0")
                    }
                }
                developers {
                    developer {
                        id.set("ronjunevaldoz")
                        name.set("Ron Valdoz")
                        email.set("ronjune.lopez@gmail.com")
                    }
                }
                scm {
                    connection.set("scm:git:git://github.com/ronjunevaldoz/jni-binding-generator.git")
                    developerConnection.set("scm:git:ssh://github.com/ronjunevaldoz/jni-binding-generator.git")
                    url.set("https://github.com/ronjunevaldoz/jni-binding-generator")
                }
            }
        }
    }
    repositories {
        mavenLocal()
    }
}
