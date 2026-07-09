## Configuring Cues

Go to the **Cues** section in the left sidebar to configure cue types and add cues to your script.

### Cue Types

The **Cue Types** tab allows you to Add, Edit, and Delete different cue types. Common examples include Lighting (LX), Sound (SND), or other technical cues specific to your production. When you first access this page, you'll see an empty cue types list:

![](../images/config_show/cue_types_empty.png)

#### Creating Cue Types

Click **New Cue Type** to create a new cue type. For each cue type, you'll need to specify:
- **Prefix**: A short identifier (e.g., "LX" for lighting, "SND" for sound)
- **Description**: A full description of the cue type
- **Color**: A color code to visually distinguish this cue type in the interface

After adding cue types, they will appear in the cue types overview:

![](../images/config_show/cue_types.png)

The color you choose will be used throughout DigiScript to make different cue types instantly recognizable during configuration and live shows.

#### Importing Cue Types from Another Show

If you have already configured cue types for another show, you can import them into the current show using the **Import Cue Type** button. This opens a panel listing all cue types from your other shows, grouped by show name. Click **Import** next to any cue type to add an independent copy to the current show — changes made after import do not affect the original show.

### Adding Cues to the Script

The **Cue Configuration** tab allows you to add cues to your script. This interface is similar to the script editing page in layout and function. When first accessed, you'll see your script without any cues:

![](../images/config_show/cue_configuration_empty.png)

#### Configuring Cues

To add cues, click **Begin Editing** to request exclusive edit access.

##### Cue Placement on Line Types

Cues can be attached to most line types in your script:

- **Dialogue Lines**: Standard placement for cues that occur during character speech
- **Stage Direction Lines**: Useful for cues that occur during action sequences or scene changes
- **Cue Lines**: Dedicated lines for placing cues without associated dialogue, particularly useful for cues between dialogue

**Note**: Spacing lines do not support cues, as they are designed purely for visual spacing and are hidden during live shows.

##### Adding Cues

To add a new cue:
1. Click the green **+** button next to the script line where the cue should occur
2. A chooser dialog appears — select **Individual Cue** to add a single cue, or **Cue Group** to bundle multiple cues together (see below)
3. For an individual cue, select the cue type and provide a cue identifier (e.g., "1" for LX 1), then click **Add**

After adding cues, they will appear as colored buttons next to their associated script lines:

![](../images/config_show/cue_configuration_with_cues.png)

Clicking on a cue button allows you to **Edit** or **Delete** that cue. The cue's color matches the color you defined for its cue type, making it easy to identify different types of cues at a glance.

##### Cue Groups

When a song or sequence has many cues on the same script line (e.g., 100 LX cues for a timecoded intro), adding them all as individual buttons becomes unworkable. **Cue Groups** solve this by bundling multiple cues into a single collapsed button displaying an abbreviated label such as `LX 1 - LX 100` or `LX - Music Intro`.

To create a cue group:
1. Click the **+** button on a script line, then select **Cue Group**
2. In the **Add Cue Group** dialog:
   - Select the **Cue Type** (all cues in a group share one type)
   - Optionally enter a **Label Override** (e.g., "Music Intro") — if left blank, the label is automatically derived from the first and last cue identifiers
   - Add cues using the range input (e.g., type `1 > 100` and click **Add Range** to add 100 cues at once) or click **Add Single Cue** to add individual rows
   - Use the ↑ ↓ buttons to reorder cues within the group — the order determines the first/last identifiers shown in the label
3. Click **Save Group** to create the group

The group appears in the cue column as a button with a **dashed border**, making it visually distinct from individual cues.

Clicking a group button opens the **Edit Cue Group** dialog, where you can:
- Change the label override
- Add, reorder, or remove individual cues within the group
- Use **Delete Group** to remove the group and all its cues

A script line can freely mix individual cues and groups simultaneously. The label preview in the dialog updates live as you make changes.

### Renumbering Cues

The **Renumber Cues** feature resynchronises DigiScript's cue identifiers after you perform a renum/reorder on your MagicQ lighting console. When MagicQ collapses point cues (e.g. 3.1, 3.2) into sequential integers, DigiScript's cue identifiers become stale — this feature updates them to match.

#### When to use it

Use Renumber Cues after performing a renum/reorder on your MagicQ console. Export the **before-renum** cue stack from MagicQ first (see below), then use it to guide the renumber in DigiScript.

#### How it works

MagicQ sorts all cues in the stack numerically and reassigns sequential integers starting at 1. DigiScript replicates this by reading the full cue list from a MagicQ CSV export, so it can correctly place the cues it knows about — even when some console cues are intentionally omitted from the script.

For example, if the console has cues 1, 2, 2.1, 3, 4 but DigiScript only has 1 and 3:

| Console cues | After MagicQ renum | DigiScript before | DigiScript after |
|---|---|---|---|
| 1, 2, 2.1, 3, 4 | 1, 2, 3, 4, 5 | 1, 3 | 1, 4 |

DigiScript's "3" becomes "4" because cue 2.1 occupies position 3 in the full sequence — even though 2.1 is not in DigiScript.

#### Exporting the CSV from MagicQ

Before running a renum in MagicQ, export the cue stack window as a CSV:

1. In MagicQ, open the **Cue Stack** window for your show
2. Press the **Cue Stack** title bar and choose **Export to CSV**
3. Save the file to your computer

The exported file contains a `Cue id` column with the pre-renum cue numbers — this is the file to upload.

#### Accessing the feature in DigiScript

1. Navigate to **Cues → Cue Configuration**
2. Click the **Renumber Cues** button in the toolbar

#### Step 1 — Configure

- **MagicQ Cue Stack CSV (before renumber)**: Upload the CSV exported from MagicQ before the renum was run. Once a valid file is loaded, a confirmation line shows how many cues were found.
- **Cue Types to Renumber**: Check one or more cue types. All checked types are processed together against the same CSV mapping.

The **Next** button is enabled once both a valid CSV has been loaded and at least one cue type is selected.

Click **Next** to preview the changes.

#### Step 2 — Preview

The preview shows two sections:

**Changed Cues** — cues whose identifier will change. The table shows the current identifier and the proposed new identifier. You can edit the proposed new identifier if needed.

**Unmatched Cues** — cues that are skipped by default for one of two reasons:

- The cue's numeric identifier (or prefix) was not found in the uploaded CSV — for example, a cue that no longer exists on the console
- The cue has no numeric identifier at all (e.g. free-form text like "INTRO")

For text-suffix cues (e.g. "2.1 - Blackout") where the numeric prefix *is* found in the CSV, DigiScript pre-fills the suggested new identifier (e.g. "3 - Blackout") so you can include it with one click.

Tick the **Include** checkbox next to any unmatched cue you want to reassign, and adjust the new identifier if needed.

DigiScript validates that all final identifiers within each cue type are unique and non-empty. The **Confirm Renumber** button remains disabled until validation passes.

Click **Confirm Renumber** to apply the changes, or **Back** to return to the configuration step.

#### What is not changed

- `label_override` on cue groups is preserved
- Group membership and sort order within groups are unchanged
- Script positions (which line a cue is on) are unchanged
- Cues in other script revisions are not affected

### Cues and Script Revisions

Cues are tied to script revisions - when you add or modify cues, the changes only affect the currently loaded revision. This allows you to maintain different cue configurations for different versions of your script.

Once you've configured your cues, you're ready to run a [Live Show](./live_show.md).