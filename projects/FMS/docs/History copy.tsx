import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { boardNum } from "../../component/function/amount_format";
import { StorageListType } from "../../component/interface/storage";
import { fontStyles } from "../../component/style/common_font";
import Common_Layout from "../../component/style/common_Layout";
import {
  DataNone,
  mainBlue,
  lightBlue,
  RowView,
  RowView2,
  Title,
} from "../../component/style/common_style";
import PagingControl from "../../component/UI/PagingControl";
import { ReactComponent as IconDownload } from "../../img/icon_download.svg";
import { ReactComponent as IconMoreActive } from "../../img/icon_more_active.svg";
import { ReactComponent as IconMoreDeactive } from "../../img/icon_more_deactive.svg";
import { ReactComponent as IconRefresh } from "../../img/icon_refresh.svg";
import { ReactComponent as IconSearch } from "../../img/icon_search.svg";
import { storageAPI } from "./api/material";
import useHistoryList, { FilterKey } from "./hook/useHistoryList";
import useMeterialList from "./hook/useMeterialList";
import FilterModal, { FilterOption } from "./modal/FilterModal";

const typeClassName = (type: string | number) => {
  if (type === 0) return "gray";
  if (type === "삭제") return "red";
  if (type === "수정") return "blue";
  return;
};

/** 상태(구분)는 고정값 */
const STATUS_OPTIONS = ["입고", "출고", "이동", "등록", "수정", "삭제"];

/** 하단 검색 대상 항목 (드롭다운) */
const SEARCH_OPTIONS = [
  { key: "mat_name", label: "자재명" },
  { key: "sto_name", label: "보관 위치" },
  { key: "worker", label: "담당자" },
  { key: "his_note", label: "상세내용" },
];

type OpenModal = FilterKey | null;

/** 카테고리 드롭다운 + 검색창 통합 바 */
const CombinedSearch = ({
  searchKey,
  onKeyChange,
  onSearch,
}: {
  searchKey: string;
  onKeyChange: (e: ChangeEvent<HTMLSelectElement>) => void;
  onSearch: (v: string) => void;
}) => {
  const [keyword, setKeyword] = useState("");
  const label = SEARCH_OPTIONS.find((o) => o.key === searchKey)?.label ?? "";
  return (
    <SearchWrap>
      <select value={searchKey} onChange={onKeyChange}>
        {SEARCH_OPTIONS.map((o) => (
          <option key={o.key} value={o.key}>
            {o.label}
          </option>
        ))}
      </select>
      <span className="divider" />
      <input
        placeholder={`${label}을(를) 입력해주세요.`}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSearch(keyword)}
      />
      <IconSearch onClick={() => onSearch(keyword)} />
    </SearchWrap>
  );
};

const Inventory_History = () => {
  const Navigate = useNavigate();
  const { list, paging, search, filters, period } = useHistoryList();

  const [openModal, setOpenModal] = useState<OpenModal>(null);

  // 옵션 소스 (기존 마스터 목록)
  const { list: materialList } = useMeterialList({ open: true }); // 자재+규격 전체
  const [storageList, setStorageList] = useState<StorageListType[]>([]);
  useEffect(() => {
    storageAPI
      .load()
      .then((d) => setStorageList(d.storageList || []))
      .catch(() => { });
  }, []);

  // 담당자: 이력에 등장하는 고유값 (누적) — 백엔드 distinct 엔드포인트 나오면 교체
  const [workerOptions, setWorkerOptions] = useState<string[]>([]);
  useEffect(() => {
    setWorkerOptions((prev) => {
      const set = new Set(prev);
      list.forEach((d) => {
        const w = d.worker?.replace("null", "").trim();
        if (w) set.add(w);
      });
      return Array.from(set);
    });
  }, [list]);

  // 모달별 옵션/설정
  const materialItems: FilterOption[] = useMemo(
    () =>
      materialList.map((m) => ({
        id: m.mat_seq,
        mat_name: m.mat_name,
        mat_size: m.mat_size || "-",
        _size: m.mat_size,
      })),
    [materialList]
  );
  const storageItems: FilterOption[] = useMemo(
    () =>
      storageList.map((s) => ({
        id: s.storage_sto_seq,
        sto_name: s.storage_sto_name,
      })),
    [storageList]
  );
  const statusItems: FilterOption[] = STATUS_OPTIONS.map((s) => ({
    id: s,
    name: s,
  }));
  const workerItems: FilterOption[] = workerOptions.map((w) => ({
    id: w,
    worker: w,
  }));

  // 선택된 필터 칩 (모두 합침)
  const chips = [
    ...filters.materials.map((i) => ({ key: "materials" as FilterKey, ...i })),
    ...filters.statuses.map((i) => ({ key: "statuses" as FilterKey, ...i })),
    ...filters.storages.map((i) => ({ key: "storages" as FilterKey, ...i })),
    ...filters.workers.map((i) => ({ key: "workers" as FilterKey, ...i })),
  ];

  const headIcon = (active: boolean) =>
    active ? <IconMoreActive /> : <IconMoreDeactive />;

  // 엑셀 다운로드 — TODO: 백엔드 엑셀 export 연동 예정
  const handleExcel = () => {
    alert("엑셀 다운로드 기능은 준비 중입니다.");
  };

  return (
    <Common_Layout mainmenu={"자재 관리"} submenu={"이력 조회"}>
      <Title>
        <div className="title">이력 조회</div>
        <div className="description">
          적정 재고와 현재 재고를 비교하여 관리할 수 있습니다.
        </div>
      </Title>

      <RowView>
        <SubTitleArea>
          전체 <span>{paging.cnt}</span>
        </SubTitleArea>

        <RowView2 style={{ gap: "0.4rem" }}>
          <ExcelBtn onClick={handleExcel}>
            <IconDownload />
            엑셀 다운
          </ExcelBtn>
          <DateInput
            type="date"
            value={period.start}
            max={period.end || undefined}
            onChange={period.setStart}
          />
          <span>~</span>
          <DateInput
            type="date"
            value={period.end}
            min={period.start || undefined}
            onChange={period.setEnd}
          />
          <ResetBtn onClick={filters.clearAll}>
            <IconRefresh />
            초기화
          </ResetBtn>
        </RowView2>
      </RowView>

      {chips.length > 0 && (
        <ChipArea>
          {chips.map((c) => (
            <Chip key={`${c.key}-${c.id}`}>
              {c.label}
              <span onClick={() => filters.removeChip(c.key, c.id)}>✕</span>
            </Chip>
          ))}
        </ChipArea>
      )}

      <Header>
        <div style={{ flex: 0.5, border: 0 }}>구분</div>
        <div>날짜</div>
        <div className="filter" onClick={() => setOpenModal("materials")}>
          자재명 {headIcon(filters.materials.length > 0)}
        </div>
        <div className="filter" onClick={() => setOpenModal("materials")}>
          규격 {headIcon(filters.materials.length > 0)}
        </div>
        <div
          style={{ flex: 0.5 }}
          className="filter"
          onClick={() => setOpenModal("statuses")}
        >
          상태 {headIcon(filters.statuses.length > 0)}
        </div>
        <div style={{ flex: 0.5 }}>수량</div>
        <div style={{ flex: 0.5 }}>현재 재고</div>
        <div className="filter" onClick={() => setOpenModal("storages")}>
          위치 {headIcon(filters.storages.length > 0)}
        </div>
        <div className="filter" onClick={() => setOpenModal("workers")}>
          담당자 {headIcon(filters.workers.length > 0)}
        </div>
        <div style={{ flex: 2 }}>상세내용</div>
      </Header>

      {paging.cnt === 0 ? (
        <DataNone>등록된 데이터가 없습니다</DataNone>
      ) : (
        list.map((data, idx) => {
          return (
            <Row key={idx}>
              <DataListCol onClick={() => Navigate(`${data.his_seq}`)}>
                <div style={{ flex: 0.5, border: 0 }}>
                  {boardNum(idx, paging.currentpage, paging.perPage)}
                </div>
                <div>{data.his_dt}</div>
                <div>{data.mat_name}</div>
                <div>{data.mat_size || "-"}</div>
                <div
                  style={{ flex: 0.5 }}
                  className={typeClassName(data.his_type)}
                >
                  {data.his_type}
                </div>
                <div style={{ flex: 0.5 }}>{data.his_cnt || "-"}</div>
                <div
                  style={{ flex: 0.5 }}
                  className={typeClassName(data.his_stock)}
                >
                  {data.his_stock}
                </div>
                <div>{data.sto_name}</div>
                <div>{data.worker?.replace("null", "")}</div>
                <div style={{ flex: 2 }}>{data.his_note || "-"}</div>
              </DataListCol>
            </Row>
          );
        })
      )}

      <BottomArea>
        <CombinedSearch
          searchKey={search.key}
          onKeyChange={search.settingKey}
          onSearch={search.setting}
        />
        <PageSizeSelect
          value={paging.perPage}
          onChange={paging.setPerPage}
        >
          {[10, 20, 30, 40, 50].map((n) => (
            <option key={n} value={n}>
              {n}개씩 보기
            </option>
          ))}
        </PageSizeSelect>
      </BottomArea>

      <PagingControl
        cnt={paging.cnt}
        currentpage={paging.currentpage}
        setCurrentpage={paging.setCurrentpage}
        perPage={paging.perPage}
      />

      {/* 자재 및 규격 선택 */}
      <FilterModal
        open={openModal === "materials"}
        title="자재 및 규격 선택"
        width={36}
        total={materialItems.length}
        columns={[
          { key: "mat_name", label: "자재명" },
          { key: "mat_size", label: "규격" },
        ]}
        items={materialItems}
        selectedIds={filters.materials.map((i) => i.id)}
        buildLabel={(it) =>
          it._size ? `${it.mat_name}/${it._size}` : it.mat_name
        }
        onClose={() => setOpenModal(null)}
        onConfirm={(sel) => filters.applyFilter("materials", sel)}
      />

      {/* 상태 선택 */}
      <FilterModal
        open={openModal === "statuses"}
        title="상태 선택"
        width={22}
        columns={[{ key: "name", label: "상태명" }]}
        items={statusItems}
        selectedIds={filters.statuses.map((i) => i.id)}
        buildLabel={(it) => it.name}
        onClose={() => setOpenModal(null)}
        onConfirm={(sel) => filters.applyFilter("statuses", sel)}
      />

      {/* 보관위치 선택 */}
      <FilterModal
        open={openModal === "storages"}
        title="보관위치 선택"
        width={32}
        columns={[{ key: "sto_name", label: "보관 위치" }]}
        items={storageItems}
        selectedIds={filters.storages.map((i) => i.id)}
        buildLabel={(it) => it.sto_name}
        onClose={() => setOpenModal(null)}
        onConfirm={(sel) => filters.applyFilter("storages", sel)}
      />

      {/* 담당자 선택 */}
      <FilterModal
        open={openModal === "workers"}
        title="담당자 선택"
        width={32}
        columns={[{ key: "worker", label: "담당자" }]}
        items={workerItems}
        selectedIds={filters.workers.map((i) => i.id)}
        buildLabel={(it) => it.worker}
        onClose={() => setOpenModal(null)}
        onConfirm={(sel) => filters.applyFilter("workers", sel)}
      />
    </Common_Layout>
  );
};

export default Inventory_History;

const SubTitleArea = styled.div`
  span {
    ${fontStyles.medium}
    color: ${mainBlue};
  }
`;
const BTN_HEIGHT = "2.2rem";
const ExcelBtn = styled.button`
  box-sizing: border-box;
  height: ${BTN_HEIGHT};
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.9rem;
  background: white;
  border: 1px solid ${mainBlue};
  border-radius: 4px;
  color: ${mainBlue};
  font-weight: 500;
  cursor: pointer;
  &:hover {
    background: ${lightBlue};
  }
  svg {
    width: 14px;
    height: 14px;
  }
`;
const DateInput = styled.input`
  box-sizing: border-box;
  height: ${BTN_HEIGHT};
  padding: 0 0.6rem;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  color: #555;
  &:hover,
  &:focus {
    border-color: #1d1d1d;
  }
`;
const ResetBtn = styled.button`
  box-sizing: border-box;
  height: ${BTN_HEIGHT};
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.8rem;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  color: #555;
  cursor: pointer;
  &:hover {
    border-color: ${mainBlue};
    color: ${mainBlue};
  }
  svg {
    width: 14px;
    height: 14px;
  }
`;
const BottomArea = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 1.5rem;
`;
const SearchWrap = styled(RowView2)`
  box-sizing: border-box;
  width: 32rem;
  max-width: 100%;
  height: 2.4rem;
  border: 1px solid #dddddd;
  border-radius: 4px;
  padding: 0 0.6rem;
  select {
    border: 0;
    background: transparent;
    cursor: pointer;
    color: #333;
    outline: 0;
  }
  span.divider {
    width: 1px;
    height: 1.2rem;
    background: #e0e0e0;
    margin: 0 0.6rem;
  }
  input {
    flex: 1;
    border: 0;
    outline: 0;
    min-width: 0;
  }
  svg {
    cursor: pointer;
    margin-left: 0.4rem;
  }
`;
const PageSizeSelect = styled.select`
  position: absolute;
  right: 0;
  padding: 5px 0.6rem;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  color: #555;
`;
const ChipArea = styled(RowView2)`
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.6rem 0;
`;
const Chip = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.6rem;
  background: none;
  color: #757575;
  border: 1px solid #e8e8e8;
  border-radius: 999px;
  font-size: 13px;
  span {
    cursor: pointer;
    font-size: 11px;
    color: #999;
  }
`;
const Row = styled.div`
  :hover {
    background-color: ${lightBlue};
  }
`;
const Header = styled(RowView2)`
  margin-top: 0.5rem;
  ${fontStyles.medium}
  color: #757575;
  border: 1px solid #eeeeee;
  background-color: #fafafa;
  div {
    flex: 1;
    padding: 0.7rem 0.5rem;
    text-align: center;
    border-left: 1px solid #eeeeee;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  div.filter {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    cursor: pointer;
    user-select: none;
  }
  div.filter svg {
    width: 14px;
    height: 14px;
  }
  span {
    width: 3rem;
  }
`;
const DataListCol = styled(RowView)`
  border: 1px solid #eeeeee;
  border-top: 0;
  cursor: pointer;
  div {
    flex: 1;
    padding: 0.7rem 0.5rem;
    text-align: center;
    border-left: 1px solid #eeeeee;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  div.red {
    color: #fe5a44;
  }
  div.blue {
    color: #5ca6ff;
  }
  div.gray {
    color: #a9a9ab;
  }
`;
