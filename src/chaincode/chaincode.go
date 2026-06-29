package main

import (
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

type SmartContract struct {
	contractapi.Contract
}

type Account struct {
	ID      string `json:"id"`
	Balance int    `json:"balance"`
}

type Inventory struct {
	ID        string `json:"id"`
	Warehouse string `json:"warehouse"`
	SKU       string `json:"sku"`
	Quantity  int    `json:"quantity"`
}

type Batch struct {
	ID     string `json:"id"`
	Status string `json:"status"`
}

type InventoryTransferOp struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	SKU         string `json:"sku"`
	Quantity    int    `json:"quantity"`
}

type InventoryAudit struct {
	Total int                  `json:"total"`
	Items map[string]Inventory `json:"items"`
}

func (s *SmartContract) InitAccounts(ctx contractapi.TransactionContextInterface, countText string, balanceText string) error {
	count, err := strconv.Atoi(countText)
	if err != nil || count <= 0 {
		return fmt.Errorf("invalid account count: %s", countText)
	}
	balance, err := strconv.Atoi(balanceText)
	if err != nil || balance < 0 {
		return fmt.Errorf("invalid balance: %s", balanceText)
	}
	for i := 0; i < count; i++ {
		id := fmt.Sprintf("acct%06d", i)
		account := Account{ID: id, Balance: balance}
		data, err := json.Marshal(account)
		if err != nil {
			return err
		}
		if err := ctx.GetStub().PutState(id, data); err != nil {
			return err
		}
	}
	return nil
}

func (s *SmartContract) ReadAccount(ctx contractapi.TransactionContextInterface, id string) (*Account, error) {
	return getAccount(ctx, id)
}

func (s *SmartContract) Transfer(ctx contractapi.TransactionContextInterface, from string, to string, amountText string) error {
	if from == to {
		return fmt.Errorf("from and to must differ")
	}
	amount, err := strconv.Atoi(amountText)
	if err != nil || amount <= 0 {
		return fmt.Errorf("invalid amount: %s", amountText)
	}
	fromAccount, err := getAccount(ctx, from)
	if err != nil {
		return err
	}
	toAccount, err := getAccount(ctx, to)
	if err != nil {
		return err
	}
	if fromAccount.Balance < amount {
		return fmt.Errorf("insufficient balance in %s", from)
	}
	fromAccount.Balance -= amount
	toAccount.Balance += amount
	if err := putAccount(ctx, fromAccount); err != nil {
		return err
	}
	return putAccount(ctx, toAccount)
}

type TransferOp struct {
	From   string `json:"from"`
	To     string `json:"to"`
	Amount int    `json:"amount"`
}

func (s *SmartContract) BatchTransfer(ctx contractapi.TransactionContextInterface, operationsText string) error {
	var operations []TransferOp
	if err := json.Unmarshal([]byte(operationsText), &operations); err != nil {
		return fmt.Errorf("invalid batch transfer json: %w", err)
	}
	if len(operations) == 0 {
		return fmt.Errorf("batch transfer requires at least one operation")
	}

	accounts := make(map[string]*Account)
	for _, op := range operations {
		if op.From == "" || op.To == "" || op.From == op.To {
			return fmt.Errorf("invalid transfer operation")
		}
		if op.Amount <= 0 {
			return fmt.Errorf("invalid transfer amount: %d", op.Amount)
		}
		if _, ok := accounts[op.From]; !ok {
			account, err := getAccount(ctx, op.From)
			if err != nil {
				return err
			}
			accounts[op.From] = account
		}
		if _, ok := accounts[op.To]; !ok {
			account, err := getAccount(ctx, op.To)
			if err != nil {
				return err
			}
			accounts[op.To] = account
		}
	}

	for _, op := range operations {
		fromAccount := accounts[op.From]
		toAccount := accounts[op.To]
		if fromAccount.Balance < op.Amount {
			return fmt.Errorf("insufficient balance in %s", op.From)
		}
		fromAccount.Balance -= op.Amount
		toAccount.Balance += op.Amount
	}

	for _, account := range accounts {
		if err := putAccount(ctx, account); err != nil {
			return err
		}
	}
	return nil
}

func (s *SmartContract) AuditAccounts(ctx contractapi.TransactionContextInterface, accountsText string) (int, error) {
	var ids []string
	if err := json.Unmarshal([]byte(accountsText), &ids); err != nil {
		return 0, fmt.Errorf("invalid audit accounts json: %w", err)
	}
	total := 0
	for _, id := range ids {
		account, err := getAccount(ctx, id)
		if err != nil {
			return 0, err
		}
		total += account.Balance
	}
	return total, nil
}

func (s *SmartContract) UpdateOne(ctx contractapi.TransactionContextInterface, id string, deltaText string) error {
	delta, err := strconv.Atoi(deltaText)
	if err != nil {
		return fmt.Errorf("invalid delta: %s", deltaText)
	}
	account, err := getAccount(ctx, id)
	if err != nil {
		return err
	}
	account.Balance += delta
	return putAccount(ctx, account)
}

func (s *SmartContract) InitSupplyChain(ctx contractapi.TransactionContextInterface, warehouseCountText string, skuCountText string, quantityText string, batchCountText string) error {
	warehouseCount, err := parsePositiveInt("warehouse count", warehouseCountText)
	if err != nil {
		return err
	}
	skuCount, err := parsePositiveInt("SKU count", skuCountText)
	if err != nil {
		return err
	}
	quantity, err := parseNonNegativeInt("initial quantity", quantityText)
	if err != nil {
		return err
	}
	batchCount, err := parsePositiveInt("batch count", batchCountText)
	if err != nil {
		return err
	}

	for warehouseIndex := 0; warehouseIndex < warehouseCount; warehouseIndex++ {
		warehouse := fmt.Sprintf("wh%03d", warehouseIndex)
		for skuIndex := 0; skuIndex < skuCount; skuIndex++ {
			sku := fmt.Sprintf("sku%05d", skuIndex)
			inventory := Inventory{
				ID:        inventoryKey(warehouse, sku),
				Warehouse: warehouse,
				SKU:       sku,
				Quantity:  quantity,
			}
			if err := putInventory(ctx, &inventory); err != nil {
				return err
			}
		}
	}

	for batchIndex := 0; batchIndex < batchCount; batchIndex++ {
		batch := Batch{
			ID:     fmt.Sprintf("batch%06d", batchIndex),
			Status: "CREATED",
		}
		if err := putBatch(ctx, &batch); err != nil {
			return err
		}
	}
	return nil
}

func (s *SmartContract) ReadInventory(ctx contractapi.TransactionContextInterface, warehouse string, sku string) (*Inventory, error) {
	return getInventory(ctx, warehouse, sku)
}

func (s *SmartContract) TransferInventory(ctx contractapi.TransactionContextInterface, source string, destination string, sku string, quantityText string) error {
	quantity, err := parsePositiveInt("transfer quantity", quantityText)
	if err != nil {
		return err
	}
	return applyInventoryTransfer(ctx, make(map[string]*Inventory), InventoryTransferOp{
		Source: source, Destination: destination, SKU: sku, Quantity: quantity,
	}, true)
}

func (s *SmartContract) BatchTransferInventory(ctx contractapi.TransactionContextInterface, operationsText string) error {
	var operations []InventoryTransferOp
	if err := json.Unmarshal([]byte(operationsText), &operations); err != nil {
		return fmt.Errorf("invalid batch inventory transfer json: %w", err)
	}
	if len(operations) == 0 {
		return fmt.Errorf("batch inventory transfer requires at least one operation")
	}

	inventories := make(map[string]*Inventory)
	for _, op := range operations {
		if err := validateInventoryTransfer(op); err != nil {
			return err
		}
		for _, warehouse := range []string{op.Source, op.Destination} {
			key := inventoryKey(warehouse, op.SKU)
			if _, ok := inventories[key]; !ok {
				inventory, err := getInventory(ctx, warehouse, op.SKU)
				if err != nil {
					return err
				}
				inventories[key] = inventory
			}
		}
	}

	for _, op := range operations {
		if err := applyInventoryTransfer(ctx, inventories, op, false); err != nil {
			return err
		}
	}
	for _, inventory := range inventories {
		if err := putInventory(ctx, inventory); err != nil {
			return err
		}
	}
	return nil
}

func (s *SmartContract) UpdateBatchStatus(ctx contractapi.TransactionContextInterface, batchID string, nextStatus string) error {
	batch, err := getBatch(ctx, batchID)
	if err != nil {
		return err
	}
	if batch.Status == nextStatus {
		return putBatch(ctx, batch)
	}
	allowed := map[string]map[string]bool{
		"CREATED":    {"DISPATCHED": true},
		"DISPATCHED": {"IN_TRANSIT": true, "RECALLED": true},
		"IN_TRANSIT": {"RECEIVED": true, "RECALLED": true},
		"RECEIVED":   {},
		"RECALLED":   {},
	}
	if !allowed[batch.Status][nextStatus] {
		return fmt.Errorf("invalid batch status transition: %s -> %s", batch.Status, nextStatus)
	}
	batch.Status = nextStatus
	return putBatch(ctx, batch)
}

func (s *SmartContract) AuditInventory(ctx contractapi.TransactionContextInterface, inventoryKeysText string) (*InventoryAudit, error) {
	var keys []string
	if err := json.Unmarshal([]byte(inventoryKeysText), &keys); err != nil {
		return nil, fmt.Errorf("invalid inventory audit json: %w", err)
	}
	if len(keys) == 0 {
		return nil, fmt.Errorf("inventory audit requires at least one key")
	}
	result := &InventoryAudit{Items: make(map[string]Inventory)}
	for _, key := range keys {
		data, err := ctx.GetStub().GetState(key)
		if err != nil {
			return nil, err
		}
		if data == nil {
			return nil, fmt.Errorf("inventory %s does not exist", key)
		}
		var inventory Inventory
		if err := json.Unmarshal(data, &inventory); err != nil {
			return nil, err
		}
		if inventory.Quantity < 0 {
			return nil, fmt.Errorf("negative inventory at %s", key)
		}
		result.Total += inventory.Quantity
		result.Items[key] = inventory
	}
	return result, nil
}

func applyInventoryTransfer(ctx contractapi.TransactionContextInterface, inventories map[string]*Inventory, op InventoryTransferOp, persist bool) error {
	if err := validateInventoryTransfer(op); err != nil {
		return err
	}
	sourceKey := inventoryKey(op.Source, op.SKU)
	destinationKey := inventoryKey(op.Destination, op.SKU)
	sourceInventory := inventories[sourceKey]
	destinationInventory := inventories[destinationKey]
	var err error
	if sourceInventory == nil {
		sourceInventory, err = getInventory(ctx, op.Source, op.SKU)
		if err != nil {
			return err
		}
	}
	if destinationInventory == nil {
		destinationInventory, err = getInventory(ctx, op.Destination, op.SKU)
		if err != nil {
			return err
		}
	}
	if sourceInventory.Quantity < op.Quantity {
		return fmt.Errorf("insufficient inventory in %s", sourceKey)
	}
	sourceInventory.Quantity -= op.Quantity
	destinationInventory.Quantity += op.Quantity
	inventories[sourceKey] = sourceInventory
	inventories[destinationKey] = destinationInventory
	if persist {
		if err := putInventory(ctx, sourceInventory); err != nil {
			return err
		}
		return putInventory(ctx, destinationInventory)
	}
	return nil
}

func validateInventoryTransfer(op InventoryTransferOp) error {
	if op.Source == "" || op.Destination == "" || op.Source == op.Destination {
		return fmt.Errorf("source and destination warehouses must be non-empty and different")
	}
	if op.SKU == "" {
		return fmt.Errorf("SKU must be non-empty")
	}
	if op.Quantity <= 0 {
		return fmt.Errorf("transfer quantity must be positive")
	}
	return nil
}

func inventoryKey(warehouse string, sku string) string {
	return fmt.Sprintf("inv:%s:%s", warehouse, sku)
}

func getInventory(ctx contractapi.TransactionContextInterface, warehouse string, sku string) (*Inventory, error) {
	key := inventoryKey(warehouse, sku)
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("inventory %s does not exist", key)
	}
	var inventory Inventory
	if err := json.Unmarshal(data, &inventory); err != nil {
		return nil, err
	}
	return &inventory, nil
}

func putInventory(ctx contractapi.TransactionContextInterface, inventory *Inventory) error {
	if inventory.Quantity < 0 {
		return fmt.Errorf("negative inventory at %s", inventory.ID)
	}
	data, err := json.Marshal(inventory)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(inventory.ID, data)
}

func getBatch(ctx contractapi.TransactionContextInterface, batchID string) (*Batch, error) {
	data, err := ctx.GetStub().GetState("batch:" + batchID)
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("batch %s does not exist", batchID)
	}
	var batch Batch
	if err := json.Unmarshal(data, &batch); err != nil {
		return nil, err
	}
	return &batch, nil
}

func putBatch(ctx contractapi.TransactionContextInterface, batch *Batch) error {
	data, err := json.Marshal(batch)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState("batch:"+batch.ID, data)
}

func parsePositiveInt(label string, value string) (int, error) {
	number, err := strconv.Atoi(value)
	if err != nil || number <= 0 {
		return 0, fmt.Errorf("invalid %s: %s", label, value)
	}
	return number, nil
}

func parseNonNegativeInt(label string, value string) (int, error) {
	number, err := strconv.Atoi(value)
	if err != nil || number < 0 {
		return 0, fmt.Errorf("invalid %s: %s", label, value)
	}
	return number, nil
}

func getAccount(ctx contractapi.TransactionContextInterface, id string) (*Account, error) {
	data, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("account %s does not exist", id)
	}
	var account Account
	if err := json.Unmarshal(data, &account); err != nil {
		return nil, err
	}
	return &account, nil
}

func putAccount(ctx contractapi.TransactionContextInterface, account *Account) error {
	data, err := json.Marshal(account)
	if err != nil {
		return err
	}
	return ctx.GetStub().PutState(account.ID, data)
}

func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		panic(err)
	}
	if err := chaincode.Start(); err != nil {
		panic(err)
	}
}
