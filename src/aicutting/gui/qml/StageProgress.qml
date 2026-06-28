import QtQuick
import "."

Column {
    id: root
    property int stage: -1
    property string message: ""
    spacing: Theme.s3
    readonly property var labels: ["INGEST", "WATCH", "DIRECT", "CUT", "RENDER"]

    Row {
        spacing: Theme.s2
        Repeater {
            model: root.labels
            Column {
                spacing: 9
                Rectangle {
                    id: bar
                    width: 132; height: 4; radius: 2; clip: true
                    color: index < root.stage ? Theme.success
                         : index === root.stage ? Theme.accent : Theme.hairline
                    Behavior on color { ColorAnimation { duration: Theme.tControl } }
                    Rectangle {  // travelling key-light on the active stage
                        visible: index === root.stage
                        width: 30; height: parent.height; radius: 2; color: Theme.accentHot
                        SequentialAnimation on x {
                            running: index === root.stage; loops: Animation.Infinite
                            NumberAnimation { from: 0; to: 102; duration: 1100; easing.type: Easing.InOutSine }
                            NumberAnimation { from: 102; to: 0; duration: 1100; easing.type: Easing.InOutSine }
                        }
                    }
                }
                Text {
                    text: modelData
                    font.family: Theme.fontDisplay; font.pixelSize: 12; font.letterSpacing: 1.8
                    color: index <= root.stage ? Theme.textHi : Theme.textLow
                }
            }
        }
    }
    Text {
        text: root.message
        font.family: Theme.fontMono; font.pixelSize: 13; color: Theme.textMid
    }
}
