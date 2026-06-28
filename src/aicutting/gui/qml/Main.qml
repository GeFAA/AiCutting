import QtQuick
import QtQuick.Window
import "."

Window {
    width: 1180; height: 760
    visible: true
    title: "AiCutting Studio"
    color: Theme.canvas

    Rectangle {
        anchors.centerIn: parent
        width: 120; height: 40; radius: Theme.rMd
        color: Theme.accent
        Text { anchors.centerIn: parent; text: backend.status; color: Theme.canvas }
    }
}
