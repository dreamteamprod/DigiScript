## User Settings

DigiScript provides personal settings that each user can configure for their own account. These settings are accessed by clicking on your username in the top-right navigation bar and are organized into five tabs: About, Settings, Stage Direction Styles, Cue Colour Preferences, and API Tokens.

### About

The About tab displays information about your user account, including your username and assigned roles.

![](../images/user_settings/about_tab.png)

### Settings

The Settings tab allows you to configure personal preferences for your DigiScript experience:

![](../images/user_settings/settings_tab.png)

#### Script Autosave

Configure the script autosave interval to automatically save your script changes while editing. You can set the autosave interval in minutes, or disable autosave entirely if you prefer manual saves.

####

 Cue Position

Choose whether cues are displayed on the left or right side of the script during live shows. This allows you to customize the layout to match your workflow or screen arrangement.

### Stage Direction Styles

DigiScript allows you to customize how stage directions appear in the script with personal color and style preferences:

![](../images/user_settings/stage_direction_styles_tab.png)

You can override the system-wide stage direction styling with your own color and font style choices. This is particularly useful if you need different visual contrast or have specific accessibility needs.

### Cue Colour Preferences

DigiScript allows you to personalize the colours of cue buttons to meet your accessibility needs without affecting other users:

![](../images/user_settings/cue_colour_preferences_tab.png)

This feature is particularly useful for:
- Users with colour blindness or visual impairments
- Adapting to different lighting conditions (bright stage lights, dark control booths)
- Personal colour preferences for better readability and contrast

#### Creating a Cue Colour Override

1. Click the **New Override** button
2. Select the cue type you want to customize from the dropdown menu
3. Use the colour picker to choose your preferred colour
4. Preview how the cue button will look with your selected colour
5. Click **OK** to save the override

The preview shows the cue button with automatic text colour adjustment to ensure readability - the text colour is automatically calculated to provide optimal contrast against your chosen background colour.

#### Managing Your Overrides

- **Edit**: Modify the colour of an existing override
- **Delete**: Remove an override and revert to the show's default cue colour

**Note**: These colour overrides are personal to your account only. Other users will continue to see the show's default cue colours. Your overrides apply in both the live performance view and the configuration views.

### API Tokens

API tokens allow external applications to authenticate with DigiScript and perform actions on your behalf:

![](../images/user_settings/api_token_tab.png)

#### Generating an API Token

1. Click the **Generate Token** button
2. A new token will be created and displayed
3. **Important**: Copy this token immediately - for security reasons, you won't be able to view it again after leaving this page

#### Managing Tokens

- **Regenerate**: Creates a new token, invalidating the previous one
- **Revoke**: Permanently removes the token and prevents it from being used

API tokens should be treated like passwords and kept secure. If you believe a token has been compromised, regenerate or revoke it immediately.