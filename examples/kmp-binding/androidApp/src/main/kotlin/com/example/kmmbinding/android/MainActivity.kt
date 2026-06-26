package com.example.kmmbinding.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.kmmbinding.NativeBridge

class MainActivity : ComponentActivity() {

    private val bridge = NativeBridge()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DemoScreen(bridge)
                }
            }
        }
    }
}

@Composable
fun DemoScreen(bridge: NativeBridge) {
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
        // once the native implementation is filled in.
    }
}
