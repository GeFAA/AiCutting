import QtQuick
import QtQuick.Controls.Basic
import "."

Rectangle {
    id: root
    property string text: ""
    property string tip: ""
    signal clicked
    implicitWidth: label.width + 36
    implicitHeight: 44
    radius: Theme.rMd
    color: ma.containsMouse ? Theme.surface2 : "transparent"
    border.width: 1
    border.color: ma.containsMouse ? Theme.borderFocus : Theme.hairline
    Behavior on color { ColorAnimation { duration: Theme.tMicro } }
    Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
    ToolTip.text: root.tip
    ToolTip.delay: 500
    ToolTip.visible: root.tip !== "" && ma.containsMouse

    Text {
        id: label
        anchors.centerIn: parent; text: root.text
        font.family: Theme.fontBody; font.pixelSize: 13; color: Theme.textMid
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; onClicked: root.clicked() }
}
