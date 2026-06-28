import QtQuick
import QtQuick.Window

Window {
    width: 1180; height: 760
    visible: true
    title: "AiCutting Studio"
    color: "#0B0D10"

    Text {
        anchors.centerIn: parent
        color: "#F2F4F7"
        text: backend.status   // proves the Backend context property is wired
    }
}
