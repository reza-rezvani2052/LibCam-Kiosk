import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LibCam.Kiosk 1.0

ApplicationWindow {
    id: window
    visible: true
    width: 1220
    height: 760
    minimumWidth: 960
    minimumHeight: 690
    title: "LibCam Kiosk | ثبت عکس عضویت"
    color: "#07111f"

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b1929" }
            GradientStop { position: 0.58; color: "#07111f" }
            GradientStop { position: 1.0; color: "#111e32" }
        }
        Rectangle {
            width: 360; height: 360; radius: 180
            color: "#173e57"; opacity: 0.16
            x: parent.width - width * 0.75; y: -height * 0.48
        }
        Rectangle {
            width: 300; height: 300; radius: 150
            color: "#087f8c"; opacity: 0.10
            x: -width * 0.55; y: parent.height - height * 0.55
        }
    }

    Item {
        id: contentRoot
        objectName: "contentRoot"
        anchors.fill: parent
        anchors.margins: 22
        LayoutMirroring.enabled: true
        LayoutMirroring.childrenInherit: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 14

            // Header: identity on the right, readiness state on the left.
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                spacing: 12

                Image {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    source: "qrc:/images/app-icon.ico"
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                }

                ColumnLayout {
                    spacing: 3
                    Text {
                        text: "LibCam Kiosk"
                        color: "#f4f8fc"
                        font.family: "Segoe UI"
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "ثبت عکس برای عضویت کتابخانه"
                        color: "#93a8bb"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    Layout.preferredWidth: 190
                    Layout.preferredHeight: 40
                    radius: 20
                    color: kiosk.cameraReady && kiosk.visionReady ? "#123b3b" : "#1b2a3d"
                    border.width: 1
                    border.color: kiosk.cameraReady && kiosk.visionReady ? "#226c69" : "#34465e"
                    Behavior on color { ColorAnimation { duration: 180 } }
                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: kiosk.cameraReady && kiosk.visionReady ? "#44dfb6" : "#e3ad5c"
                        }
                        Text {
                            text: kiosk.cameraReady && kiosk.visionReady ? "آمادهٔ عکاسی" : (kiosk.cameraReady ? "در حال آماده‌سازی" : "دوربین متصل نیست")
                            color: "#dbe7f1"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            font.weight: Font.Medium
                        }
                    }
                }
            }

            // Main workspace: stable preview area plus a compact guide/status card.
            RowLayout {
                objectName: "workspace"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 300
                spacing: 16

                Rectangle {
                    id: instructionPanel
                    objectName: "instructionPanel"
                    Layout.preferredWidth: 282
                    Layout.minimumWidth: 258
                    Layout.fillHeight: true
                    radius: 22
                    color: "#14243a"
                    border.color: "#26374c"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 44
                            Layout.preferredHeight: 44
                            radius: 14
                            color: "#153b3f"
                            Text {
                                anchors.centerIn: parent
                                text: "◎"
                                color: "#44dfb6"
                                font.pixelSize: 24
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5
                            Text {
                                Layout.fillWidth: true
                                text: kiosk.isReview ? "عکس را بررسی کنید" : (kiosk.isSaved ? "عکس آماده است" : "چطور عکس بگیرم؟")
                                color: "#f1f6fb"
                                font.family: "Segoe UI"
                                font.pixelSize: 19
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: kiosk.isReview
                                    ? "پیش از ذخیره مطمئن شوید تمام صورت واضح و کامل است."
                                    : (kiosk.isSaved
                                        ? "فایل JPG آمادهٔ بارگذاری در سامانهٔ سامان است."
                                        : "روبه‌روی دوربین بایستید و صورت را در مرکز تصویر نگه دارید.")
                                color: "#a5b8ca"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                lineHeightMode: Text.FixedHeight
                                lineHeight: 17
                                wrapMode: Text.WordWrap
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: "#2a3c50"
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 11
                            visible: kiosk.isLive

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 9
                                Rectangle {
                                    Layout.preferredWidth: 31
                                    Layout.preferredHeight: 31
                                    radius: 10
                                    color: "#17364d"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "۱"
                                        color: "#69c9f3"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: "ثبت خودکار"
                                        color: "#e3edf6"
                                        font.pixelSize: 12
                                        font.bold: true
                                        font.family: "Segoe UI"
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "یکی از دست‌ها را کمی بالاتر از شانه ببرید"
                                        color: "#9cafc2"
                                        font.pixelSize: 10
                                        font.family: "Segoe UI"
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 9
                                Rectangle {
                                    Layout.preferredWidth: 31
                                    Layout.preferredHeight: 31
                                    radius: 10
                                    color: "#2f2b4a"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "۲"
                                        color: "#b7a3ff"
                                        font.pixelSize: 13
                                        font.bold: true
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: "ثبت دستی"
                                        color: "#e3edf6"
                                        font.pixelSize: 12
                                        font.bold: true
                                        font.family: "Segoe UI"
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "از دکمهٔ پایین صفحه استفاده کنید"
                                        color: "#9cafc2"
                                        font.pixelSize: 10
                                        font.family: "Segoe UI"
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 92
                            Layout.minimumHeight: 78
                            radius: 14
                            color: kiosk.statusError ? "#3b202d" : "#152c40"
                            border.color: kiosk.statusError ? "#743747" : "#2a465c"
                            Behavior on color { ColorAnimation { duration: 180 } }
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 11
                                spacing: 4
                                Text {
                                    text: kiosk.statusError ? "نیاز به بررسی" : (kiosk.isSaved ? "ذخیره شد" : "وضعیت")
                                    color: kiosk.statusError ? "#ff8998" : "#76c8e6"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    text: kiosk.statusText
                                    color: kiosk.statusError ? "#f3b4bf" : "#b4c6d8"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 4
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    id: previewCard
                    objectName: "previewCard"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 410
                    radius: 22
                    color: "#111e30"
                    border.color: "#26374c"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 17
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    text: kiosk.isReview ? "بازبینی تصویر" : (kiosk.isSaved ? "تصویر ذخیره‌شده" : "پیش‌نمایش دوربین")
                                    color: "#f1f6fb"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 17
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    text: kiosk.isReview || kiosk.isSaved ? "کادر نهایی عکس" : "صورت را در محدودهٔ دوربین قرار دهید"
                                    color: "#92a6bb"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 11
                                }
                            }
                            Rectangle {
                                radius: 11
                                color: kiosk.isReview || kiosk.isSaved ? "#173b3f" : "#263849"
                                border.color: kiosk.isReview || kiosk.isSaved ? "#286a65" : "#3b5668"
                                Layout.preferredHeight: 30
                                Layout.preferredWidth: 106
                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 7
                                    Rectangle {
                                        width: 7; height: 7; radius: 3.5
                                        color: kiosk.isReview || kiosk.isSaved ? "#44dfb6" : "#36cbb6"
                                    }
                                    Text {
                                        text: kiosk.isReview ? "بازبینی" : (kiosk.isSaved ? "ذخیره شد" : "پیش‌نمایش")
                                        color: "#d7e6ef"
                                        font.pixelSize: 11
                                        font.family: "Segoe UI"
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: videoViewport
                            objectName: "videoViewport"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 180
                            radius: 17
                            color: "#07101d"
                            border.color: "#1d3045"
                            clip: true

                            VideoFrameItem {
                                id: videoFrame
                                anchors.fill: parent
                                anchors.margins: 5
                            }

                            Rectangle {
                                anchors.fill: parent
                                radius: 17
                                visible: !kiosk.cameraReady
                                color: "#0b1727"
                                ColumnLayout {
                                    anchors.centerIn: parent
                                    spacing: 10
                                    Text {
                                        text: "◎"
                                        color: "#3b7e91"
                                        font.pixelSize: 50
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                    Text {
                                        text: "تصویر دوربین در دسترس نیست"
                                        color: "#e0eaf3"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 16
                                        font.weight: Font.DemiBold
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                    Text {
                                        text: kiosk.statusText
                                        color: "#90a5ba"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                        horizontalAlignment: Text.AlignHCenter
                                        Layout.maximumWidth: 380
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                }
                            }

                            Rectangle {
                                anchors.fill: parent
                                radius: 17
                                visible: kiosk.isProcessing
                                color: "#d707111f"
                                ColumnLayout {
                                    anchors.centerIn: parent
                                    spacing: 15
                                    Item {
                                        Layout.preferredWidth: 52
                                        Layout.preferredHeight: 52
                                        Layout.alignment: Qt.AlignHCenter
                                        Rectangle {
                                            anchors.fill: parent
                                            radius: width / 2
                                            color: "transparent"
                                            border.width: 3
                                            border.color: "#456073"
                                        }
                                        Rectangle {
                                            width: 9; height: 9; radius: 4.5
                                            color: "#44dfc2"
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            anchors.top: parent.top
                                        }
                                        RotationAnimation on rotation {
                                            from: 0; to: 360
                                            duration: 900
                                            loops: Animation.Infinite
                                            running: kiosk.isProcessing
                                        }
                                    }
                                    Text {
                                        text: "در حال آماده‌سازی عکس…"
                                        color: "#f4f8fb"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 17
                                        font.weight: Font.DemiBold
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                    Text {
                                        text: "لطفاً چند لحظه صبر کنید"
                                        color: "#a7bdcf"
                                        font.family: "Segoe UI"
                                        font.pixelSize: 12
                                        Layout.alignment: Qt.AlignHCenter
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Text {
                                text: kiosk.isLive ? "●" : "✓"
                                color: kiosk.isLive ? "#42d8bd" : "#6dd6a7"
                                font.pixelSize: 11
                            }
                            Text {
                                Layout.fillWidth: true
                                text: kiosk.isLive
                                    ? "برای ثبت خودکار، یکی از دست‌ها را بالا ببرید؛ یا از دکمهٔ پایین صفحه استفاده کنید."
                                    : (kiosk.isReview ? "عکس را بررسی و سپس ذخیره کنید." : (kiosk.isSaved ? "فایل JPG آمادهٔ بارگذاری در سامانه است." : "پردازش عکس در حال انجام است."))
                                color: "#9aafc2"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            // Dedicated action dock, outside the preview and instruction layouts.
            Rectangle {
                id: actionBar
                objectName: "actionBar"
                Layout.fillWidth: true
                Layout.preferredHeight: 84
                Layout.minimumHeight: 84
                radius: 19
                color: "#101f32"
                border.color: "#2a3d54"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    anchors.topMargin: 11
                    anchors.bottomMargin: 11
                    spacing: 12

                    RowLayout {
                        objectName: "liveActions"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14
                        visible: kiosk.isLive

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                text: "آمادهٔ ثبت عکس"
                                color: "#f0f6fb"
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "برای ثبت خودکار یکی از دست‌ها را بالا ببرید یا دکمهٔ ثبت دستی را انتخاب کنید."
                                color: "#91a7bc"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }

                        Button {
                            id: captureButton
                            objectName: "captureButton"
                            Layout.preferredWidth: 210
                            Layout.preferredHeight: 52
                            enabled: kiosk.canCapture
                            text: "گرفتن عکس"
                            font.family: "Segoe UI"
                            font.pixelSize: 15
                            font.bold: true
                            contentItem: Text {
                                text: captureButton.text
                                font: captureButton.font
                                color: captureButton.enabled ? "#071b28" : "#70808d"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 14
                                color: !captureButton.enabled ? "#dce5ed" : (captureButton.down ? "#23bda9" : (captureButton.hovered ? "#51e0ca" : "#37d5c0"))
                                Behavior on color { ColorAnimation { duration: 130 } }
                            }
                            onClicked: kiosk.captureManually()
                        }
                    }

                    RowLayout {
                        objectName: "processingActions"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12
                        visible: kiosk.isProcessing

                        Item {
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 38
                            Rectangle {
                                anchors.fill: parent
                                radius: width / 2
                                color: "transparent"
                                border.width: 3
                                border.color: "#40566c"
                            }
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: "#44dfc2"
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.top: parent.top
                            }
                            RotationAnimation on rotation {
                                from: 0; to: 360
                                duration: 900
                                loops: Animation.Infinite
                                running: kiosk.isProcessing
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                text: "در حال آماده‌سازی عکس…"
                                color: "#f0f6fb"
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: "لطفاً چند لحظه صبر کنید."
                                color: "#91a7bc"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                            }
                        }
                    }

                    RowLayout {
                        objectName: "reviewActions"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        visible: kiosk.isReview

                        Text {
                            Layout.fillWidth: true
                            text: "عکس واضح و کامل است؟ آن را ذخیره کنید."
                            color: "#dce8f2"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }

                        Button {
                            id: retakeButton
                            objectName: "retakeButton"
                            Layout.preferredWidth: 150
                            Layout.preferredHeight: 48
                            text: "تکرار عکس"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            contentItem: Text {
                                text: retakeButton.text
                                font: retakeButton.font
                                color: "#30465a"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 13
                                color: retakeButton.down ? "#e0e9f0" : (retakeButton.hovered ? "#edf3f8" : "#ffffff")
                                border.color: "#d6e0e9"
                            }
                            onClicked: kiosk.retakePhoto()
                        }

                        Button {
                            id: saveButton
                            objectName: "saveButton"
                            Layout.preferredWidth: 185
                            Layout.preferredHeight: 48
                            text: "ذخیره تصویر"
                            font.family: "Segoe UI"
                            font.pixelSize: 13
                            font.bold: true
                            contentItem: Text {
                                text: saveButton.text
                                font: saveButton.font
                                color: "#f7fbff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 13
                                color: saveButton.down ? "#127e91" : (saveButton.hovered ? "#1595a8" : "#117f96")
                            }
                            onClicked: kiosk.savePhoto()
                        }
                    }

                    RowLayout {
                        objectName: "savedActions"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10
                        visible: kiosk.isSaved

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                text: "عکس ذخیره شد"
                                color: "#f0f6fb"
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: "اکنون آن را در سامانهٔ سامان بارگذاری کنید."
                                color: "#91a7bc"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }
                        }

                        Button {
                            id: openFolderButton
                            objectName: "openFolderButton"
                            Layout.preferredWidth: 150
                            Layout.preferredHeight: 46
                            text: "باز کردن پوشه"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            contentItem: Text {
                                text: openFolderButton.text
                                font: openFolderButton.font
                                color: "#30465a"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 12
                                color: openFolderButton.hovered ? "#edf3f8" : "#ffffff"
                                border.color: "#d6e0e9"
                            }
                            onClicked: kiosk.openOutputFolder()
                        }

                        Button {
                            id: retakeSavedButton
                            objectName: "retakeSavedButton"
                            Layout.preferredWidth: 150
                            Layout.preferredHeight: 46
                            text: "گرفتن عکس جدید"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            contentItem: Text {
                                text: retakeSavedButton.text
                                font: retakeSavedButton.font
                                color: "#30465a"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 12
                                color: retakeSavedButton.hovered ? "#edf3f8" : "#ffffff"
                                border.color: "#d6e0e9"
                            }
                            onClicked: confirmRetakeDialog.open()
                        }

                        Button {
                            id: nextMemberButton
                            objectName: "nextMemberButton"
                            Layout.preferredWidth: 165
                            Layout.preferredHeight: 46
                            text: "عضو بعدی"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            contentItem: Text {
                                text: nextMemberButton.text
                                font: nextMemberButton.font
                                color: "#9c3547"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                radius: 12
                                color: nextMemberButton.hovered ? "#fff0f1" : "#fff8f8"
                                border.color: "#f0d4d8"
                            }
                            onClicked: confirmNextDialog.open()
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: confirmRetakeDialog
        modal: true
        width: 420
        title: "حذف عکس ذخیره‌شده؟"
        standardButtons: Dialog.Yes | Dialog.No
        anchors.centerIn: Overlay.overlay
        contentItem: Item {
            implicitWidth: 340
            implicitHeight: retakePrompt.implicitHeight + 8
            Text {
                id: retakePrompt
                anchors.fill: parent
                anchors.margins: 4
                text: "با ادامه، عکس فعلی حذف می‌شود تا بتوان عکس جدیدی گرفت."
                color: "#25354a"
                font.family: "Segoe UI"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
            }
        }
        onAccepted: kiosk.confirmRetake()
    }

    Dialog {
        id: confirmNextDialog
        modal: true
        width: 420
        title: "شروع برای عضو بعدی"
        standardButtons: Dialog.Yes | Dialog.No
        anchors.centerIn: Overlay.overlay
        contentItem: Item {
            implicitWidth: 340
            implicitHeight: nextPrompt.implicitHeight + 8
            Text {
                id: nextPrompt
                anchors.fill: parent
                anchors.margins: 4
                text: "عکس ذخیره‌شده پاک شود و برنامه برای عضو بعدی آماده شود؟"
                color: "#25354a"
                font.family: "Segoe UI"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
            }
        }
        onAccepted: kiosk.startNextMember()
    }

    Component.onCompleted: kiosk.attachVideoItem(videoFrame)
}
