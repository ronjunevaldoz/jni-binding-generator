package com.example.kmmbinding.desktop

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import com.example.kmmbinding.NativeBridge

fun main() = application {
    val bridge = NativeBridge()

    Window(
        onCloseRequest = ::exitApplication,
        title = "KMP JNI Demo — Desktop",
    ) {
        MaterialTheme {
            Column(modifier = Modifier.padding(24.dp)) {
                Text(
                    text = "KMP + JNI Demo",
                    style = MaterialTheme.typography.headlineMedium,
                )
                Text(
                    text = "Vocab size: ${bridge.getVocabSize(0L)}",
                    modifier = Modifier.padding(top = 8.dp),
                )
                Text(
                    text = "Context size: ${bridge.getContextSize(0L)}",
                    modifier = Modifier.padding(top = 4.dp),
                )
                // Replace 0L above with a real handle from bridge.create(modelPath, …)
            }
        }
    }
}
