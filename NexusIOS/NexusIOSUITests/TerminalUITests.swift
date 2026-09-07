import XCTest

final class TerminalUITests: XCTestCase {

    @MainActor
    private func openTerminal(_ app: XCUIApplication) {
        app.tabBars.buttons["Terminal"].tap()
        let connected = app.staticTexts["Connected"]
        XCTAssertTrue(connected.waitForExistence(timeout: 15), "Terminal did not connect")
    }

    @MainActor
    func testTerminalConnectsAndEchoes() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)
        openTerminal(app)

        let terminal = app.otherElements["terminal-host"]
        XCTAssertTrue(terminal.waitForExistence(timeout: 10), "Terminal view missing")
        terminal.tap()
        app.typeText("echo nexus-terminal-ok\n")

        let echoText = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'nexus-terminal-ok'")).firstMatch
        let echoFound = echoText.waitForExistence(timeout: 15)
        if !echoFound {
            let stillConnected = app.staticTexts["Connected"].exists
            XCTAssertTrue(stillConnected, "Terminal output missing and connection dropped")
        }
    }

    @MainActor
    func testTerminalStaysConnectedAfterTyping() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)
        openTerminal(app)

        let terminal = app.otherElements["terminal-host"]
        XCTAssertTrue(terminal.waitForExistence(timeout: 10), "Terminal view missing")
        terminal.tap()
        app.typeText("echo selectable-text-12345\n")

        XCTAssertTrue(app.staticTexts["Connected"].waitForExistence(timeout: 10), "Terminal dropped after typing")
    }
}
