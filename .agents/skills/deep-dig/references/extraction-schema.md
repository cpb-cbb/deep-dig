# Deep Dig extraction schema

Read this reference when interpreting `get_extraction` results or explaining the Excel export.

## Job

- `status`: `pending`, `running`, `completed`, `failed`, or `cancelled`.
- `total_items`, `completed_items`, `failed_items`: document-level counters.
- A completed job may still contain item-level warnings; inspect every item.

## Job item

- `file_name`, `file_hash`, `text_length`: local parser metadata.
- `status`: item lifecycle state.
- `parsed_result`: normalized extraction result when available.
- `error_code`, `error_message`: item-scoped failure details.

## Parsed result

```json
{
  "success": true,
  "samples": [
    {
      "name": "Ti-6Al-4V",
      "properties": {
        "composition": {
          "value": "Ti-6Al-4V",
          "unit": "",
          "remark": "",
          "source": "Section 2.1",
          "method": ""
        }
      },
      "measurements": [
        {
          "conditions": {},
          "performance": {},
          "remark": "",
          "source": "Figure 3"
        }
      ]
    }
  ],
  "headers": [],
  "error": null
}
```

Keep sample-level properties separate from measurement conditions and performance values. Preserve values, units, methods, remarks, and source evidence exactly as returned. Treat absent properties as missing rather than negative evidence.

